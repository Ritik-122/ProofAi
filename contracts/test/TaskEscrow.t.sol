// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {TaskEscrow} from "../src/TaskEscrow.sol";

interface Vm {
    function deal(address account, uint256 balance) external;
    function prank(address sender) external;
    function warp(uint256 timestamp) external;
    function expectRevert(bytes4 selector) external;
}

contract TaskEscrowTest {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    TaskEscrow escrow;
    address constant CREATOR = address(0xA11CE);
    address constant OTHER = address(0xB0B);
    bytes32 constant HASH = keccak256("canonical task");

    function setUp() public {
        escrow = new TaskEscrow();
        vm.deal(CREATOR, 10 ether);
        vm.deal(OTHER, 10 ether);
    }

    function fund() private returns (uint256) {
        vm.prank(CREATOR);
        return escrow.createTask{value: 1 ether}(HASH);
    }

    function testFundingAndRefundExactlyOnce() public {
        uint256 id = fund();
        require(address(escrow).balance == 1 ether);
        require(escrow.totalLocked() == 1 ether);
        require(escrow.getTask(id).creator == CREATOR);
        vm.prank(CREATOR);
        escrow.cancelTask(id);
        vm.prank(CREATOR);
        escrow.refundTask(id);
        require(CREATOR.balance == 10 ether);
        require(escrow.totalLocked() == 0);
        vm.expectRevert(TaskEscrow.InvalidState.selector);
        vm.prank(CREATOR);
        escrow.refundTask(id);
    }

    function testOwnershipEnforced() public {
        uint256 id = fund();
        vm.expectRevert(TaskEscrow.Unauthorized.selector);
        vm.prank(OTHER);
        escrow.cancelTask(id);
        vm.expectRevert(TaskEscrow.Unauthorized.selector);
        vm.prank(OTHER);
        escrow.refundTask(id);
    }

    function testRejectsDuplicateAndInvalidFunding() public {
        fund();
        vm.expectRevert(TaskEscrow.DuplicateTask.selector);
        vm.prank(CREATOR);
        escrow.createTask{value: 1 ether}(HASH);
        vm.expectRevert(TaskEscrow.InvalidFunding.selector);
        escrow.createTask(HASH);
        vm.expectRevert(TaskEscrow.InvalidFunding.selector);
        vm.prank(CREATOR);
        escrow.createTask{value: 1 ether}(bytes32(0));
    }

    function testExpiryAllowsRecovery() public {
        uint256 id = fund();
        vm.expectRevert(TaskEscrow.InvalidState.selector);
        vm.prank(CREATOR);
        escrow.refundTask(id);
        vm.warp(escrow.getTask(id).expiresAt);
        vm.prank(CREATOR);
        escrow.refundTask(id);
        require(CREATOR.balance == 10 ether);
    }

    function testFuzzFundsRemainAccounted(uint96 amount) public {
        if (amount == 0) return;
        vm.deal(CREATOR, amount);
        vm.prank(CREATOR);
        uint256 id = escrow.createTask{value: amount}(HASH);
        require(escrow.totalLocked() == amount);
        vm.prank(CREATOR);
        escrow.cancelTask(id);
        vm.prank(CREATOR);
        escrow.refundTask(id);
        require(escrow.totalLocked() == 0 && CREATOR.balance == amount);
    }
}
