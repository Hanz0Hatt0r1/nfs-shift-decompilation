// Restore the verified retail CFG gap in FUN_00d5bd30.
//@category SHIFT.Recovery

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;

public class ExtendShiftFunctionBodyD5bd30 extends GhidraScript {
    private static final long ENTRY = 0x00d5bd30L;
    private static final long FALLTHROUGH = 0x00d5be88L;
    private static final long CALL = 0x00d5beb5L;
    private static final long CALL_TARGET = 0x00408320L;
    private static final long CALL_JUMP = 0x00d5bebaL;
    private static final long CALL_JUMP_TARGET = 0x00d5becfL;
    private static final long BRANCH_JUMP = 0x00d5becfL;
    private static final long BRANCH_JUMP_TARGET = 0x00d5bed3L;
    private static final long RETURN = 0x00d5bf04L;

    @Override
    public void run() throws Exception {
        FunctionManager functions = currentProgram.getFunctionManager();
        Listing listing = currentProgram.getListing();
        Function function = functions.getFunctionAt(toAddr(ENTRY));
        if (function == null || function.getBody().getNumAddresses() != 238 ||
                !function.getBody().contains(toAddr(0x00d5be87L)) ||
                function.getBody().contains(toAddr(FALLTHROUGH)) ||
                !function.getBody().contains(toAddr(0x00d5bed1L)) ||
                !function.getBody().contains(toAddr(RETURN))) {
            throw new IllegalStateException("FUN_00d5bd30 differs from the expected frozen body");
        }

        Instruction oldTail = listing.getInstructionAt(toAddr(0x00d5be87L));
        if (oldTail == null || oldTail.getLength() != 1 ||
                !"NOP".equals(oldTail.getMnemonicString()) ||
                !toAddr(FALLTHROUGH).equals(oldTail.getFallThrough())) {
            throw new IllegalStateException("function tail does not fall through into the verified gap");
        }

        int transaction = currentProgram.startTransaction("Extend FUN_00d5bd30 over verified CFG gap");
        boolean commit = false;
        try {
            AddressSet repairedBody = new AddressSet();
            repairedBody.add(function.getBody());
            addInstructionRange(functions, listing, function, repairedBody,
                                FALLTHROUGH, CALL_JUMP + 1);
            addInstructionRange(functions, listing, function, repairedBody,
                                BRANCH_JUMP, BRANCH_JUMP + 1);

            requireFlow(listing, 0x00d5be55L, 0x00d5bed1L, true);
            requireFlow(listing, CALL, CALL_TARGET, false);
            requireFlow(listing, CALL_JUMP, CALL_JUMP_TARGET, true);
            requireFlow(listing, BRANCH_JUMP, BRANCH_JUMP_TARGET, true);
            requireInstruction(listing, FALLTHROUGH, "NOP", "90");
            requireInstruction(listing, CALL, "CALL", "e866c46aff");
            requireInstruction(listing, CALL_JUMP, "JMP", "eb13");
            requireInstruction(listing, BRANCH_JUMP, "JMP", "eb02");

            function.setBody(repairedBody);
            if (!function.getBody().contains(toAddr(CALL)) ||
                    !function.getBody().contains(toAddr(BRANCH_JUMP)) ||
                    function.getBody().contains(toAddr(0x00d5bebcL)) ||
                    function.getBody().getNumAddresses() != 292) {
                throw new IllegalStateException("Ghidra did not persist the expected repaired body");
            }
            commit = true;
            println("Extended FUN_00d5bd30 with verified normal-return path; body bytes=" +
                    function.getBody().getNumAddresses());
        }
        finally {
            currentProgram.endTransaction(transaction, commit);
        }
    }

    private void addInstructionRange(FunctionManager functions, Listing listing,
            Function function, AddressSet body, long startOffset, long endOffset)
            throws Exception {
        Address cursor = toAddr(startOffset);
        Address end = toAddr(endOffset);
        while (cursor.compareTo(end) <= 0) {
            Instruction instruction = listing.getInstructionAt(cursor);
            if (instruction == null) {
                disassemble(cursor);
                instruction = listing.getInstructionAt(cursor);
            }
            if (instruction == null || !cursor.equals(instruction.getMinAddress()) ||
                    instruction.getMaxAddress().compareTo(end) > 0) {
                throw new IllegalStateException("instruction coverage gap at " + cursor);
            }
            Function owner = functions.getFunctionContaining(cursor);
            if (owner != null && owner != function) {
                throw new IllegalStateException("extension overlaps function " + owner.getEntryPoint());
            }
            body.add(instruction.getMinAddress(), instruction.getMaxAddress());
            cursor = instruction.getMaxAddress().next();
        }
        if (!end.equals(cursor.previous())) {
            throw new IllegalStateException("range does not end on an instruction boundary: " + end);
        }
    }

    private void requireInstruction(Listing listing, long address, String mnemonic,
                                    String bytes) throws Exception {
        Instruction instruction = listing.getInstructionAt(toAddr(address));
        if (instruction == null || !mnemonic.equals(instruction.getMnemonicString()) ||
                !bytes.equals(hex(instruction.getBytes()))) {
            throw new IllegalStateException("verified instruction mismatch at " + toAddr(address));
        }
    }

    private void requireFlow(Listing listing, long address, long target,
                             boolean jump) {
        Instruction instruction = listing.getInstructionAt(toAddr(address));
        if (instruction == null || (jump ? !instruction.getFlowType().isJump()
                                         : !instruction.getFlowType().isCall())) {
            throw new IllegalStateException("verified control transfer is missing at " + toAddr(address));
        }
        Address[] flows = instruction.getFlows();
        if (flows.length != 1 || !toAddr(target).equals(flows[0])) {
            throw new IllegalStateException("control-transfer target mismatch at " + instruction.getAddress());
        }
    }

    private String hex(byte[] bytes) {
        StringBuilder value = new StringBuilder(bytes.length * 2);
        for (byte item : bytes) value.append(String.format("%02x", item & 0xff));
        return value.toString();
    }
}
