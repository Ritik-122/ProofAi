// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @notice Milestone-one funding and recovery contract. No execution or settlement yet.
/// @dev Non-upgradeable. Later milestones require a fresh testnet deployment.
contract TaskEscrow is ReentrancyGuard {
    enum TaskStatus { Open, Assigned, Submitted, Verified, Failed, Paid, Cancelled, Refunded }

    struct Task {
        address creator;
        uint256 reward;
        bytes32 taskHash;
        TaskStatus status;
        uint64 createdAt;
        uint64 expiresAt;
    }

    error InvalidTask();
    error InvalidFunding();
    error DuplicateTask();
    error Unauthorized();
    error InvalidState();
    error TransferFailed();

    uint64 public constant TASK_LIFETIME = 1 days;
    uint256 public nextTaskId = 1;
    uint256 public totalLocked;
    mapping(uint256 => Task) private tasks;
    mapping(address => mapping(bytes32 => uint256)) public taskIdByCreatorAndHash;

    event TaskCreated(uint256 indexed taskId, address indexed creator, bytes32 indexed taskHash, uint256 reward);
    event TaskCancelled(uint256 indexed taskId);
    event RefundIssued(uint256 indexed taskId, address indexed recipient, uint256 amount);

    function createTask(bytes32 taskHash) external payable returns (uint256 taskId) {
        if (msg.value == 0 || taskHash == bytes32(0)) revert InvalidFunding();
        if (taskIdByCreatorAndHash[msg.sender][taskHash] != 0) revert DuplicateTask();
        taskId = nextTaskId++;
        tasks[taskId] = Task(msg.sender, msg.value, taskHash, TaskStatus.Open,
            uint64(block.timestamp), uint64(block.timestamp + TASK_LIFETIME));
        taskIdByCreatorAndHash[msg.sender][taskHash] = taskId;
        totalLocked += msg.value;
        emit TaskCreated(taskId, msg.sender, taskHash, msg.value);
    }

    function getTask(uint256 taskId) external view returns (Task memory) {
        if (tasks[taskId].creator == address(0)) revert InvalidTask();
        return tasks[taskId];
    }

    function cancelTask(uint256 taskId) external {
        Task storage task = ownedTask(taskId);
        if (task.status != TaskStatus.Open) revert InvalidState();
        task.status = TaskStatus.Cancelled;
        emit TaskCancelled(taskId);
    }

    function refundTask(uint256 taskId) external nonReentrant {
        Task storage task = ownedTask(taskId);
        bool expired = block.timestamp >= task.expiresAt &&
            (task.status == TaskStatus.Open || task.status == TaskStatus.Assigned ||
             task.status == TaskStatus.Submitted);
        if (task.status != TaskStatus.Cancelled && task.status != TaskStatus.Failed && !expired) {
            revert InvalidState();
        }
        task.status = TaskStatus.Refunded;
        totalLocked -= task.reward;
        (bool sent,) = payable(task.creator).call{value: task.reward}("");
        if (!sent) revert TransferFailed();
        emit RefundIssued(taskId, task.creator, task.reward);
    }

    function ownedTask(uint256 taskId) private view returns (Task storage task) {
        task = tasks[taskId];
        if (task.creator == address(0)) revert InvalidTask();
        if (task.creator != msg.sender) revert Unauthorized();
    }
}
