// Extend the verified CRT initializer body with its contiguous native exit path.
//@category SHIFT.Recovery

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;

public class ExtendShiftFunctionBody extends GhidraScript {
    private static final long ENTRY = 0x0050f010L;
    private static final long OLD_END = 0x0050f3f3L;
    private static final long FALLTHROUGH_START = 0x0050f3f4L;
    private static final long FALLTHROUGH_END = 0x0050f40cL;
    private static final long FIRST_JUMP = 0x0050f41eL;
    private static final long FIRST_JUMP_TARGET = 0x0050f432L;
    private static final long EXIT_JUMP = 0x0050f463L;
    private static final long EXIT_TARGET = 0x0050f478L;
    private static final long RETURN = 0x0050f481L;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1 || parseOffset(args[0]) != ENTRY) {
            throw new IllegalArgumentException(
                "Usage: ExtendShiftFunctionBody.java 0x0050f010");
        }

        FunctionManager functions = currentProgram.getFunctionManager();
        Listing listing = currentProgram.getListing();
        Address entry = toAddr(ENTRY);
        Function function = functions.getFunctionAt(entry);
        if (function == null) throw new IllegalStateException("initializer function is missing");

        int transaction = currentProgram.startTransaction("Extend verified cinit body");
        boolean commit = false;
        try {
            Address oldEnd = toAddr(OLD_END);
            if (!function.getBody().contains(entry) ||
                    !function.getBody().contains(oldEnd) ||
                    !oldEnd.equals(function.getBody().getMaxAddress())) {
                throw new IllegalStateException("initializer body differs from the audited truncated body");
            }

            Instruction oldTail = listing.getInstructionAt(oldEnd);
            if (oldTail == null || !"NOP".equals(oldTail.getMnemonicString()) ||
                    !toAddr(FALLTHROUGH_START).equals(oldTail.getFallThrough())) {
                throw new IllegalStateException("old body tail is not the verified fall-through NOP");
            }

            AddressSet repairedBody = new AddressSet();
            repairedBody.add(function.getBody());
            addInstructionRange(functions, listing, function, repairedBody,
                                FALLTHROUGH_START, FALLTHROUGH_END, true);
            addInstructionRange(functions, listing, function, repairedBody,
                                0x0050f40dL, 0x0050f41fL, false);
            addInstructionRange(functions, listing, function, repairedBody,
                                FIRST_JUMP_TARGET, 0x0050f464L, false);
            addInstructionRange(functions, listing, function, repairedBody,
                                EXIT_TARGET, RETURN, false);

            requireJump(listing, FIRST_JUMP, FIRST_JUMP_TARGET);
            requireJump(listing, EXIT_JUMP, EXIT_TARGET);
            Instruction ret = listing.getInstructionAt(toAddr(RETURN));
            if (ret == null || !"RET".equals(ret.getMnemonicString()) ||
                    !repairedBody.contains(toAddr(RETURN))) {
                throw new IllegalStateException("verified RET is absent from the repaired body");
            }

            function.setBody(repairedBody);
            if (!function.getBody().contains(toAddr(RETURN)) ||
                    function.getBody().getNumAddresses() != repairedBody.getNumAddresses() ||
                    function.getBody().getNumAddresses() != 636) {
                throw new IllegalStateException("Ghidra did not persist the repaired body");
            }
            commit = true;
            println("Extended FUN_0050f010 with verified fall-through and exit blocks; body bytes=" +
                    function.getBody().getNumAddresses());
        }
        finally {
            currentProgram.endTransaction(transaction, commit);
        }
    }

    private void addInstructionRange(FunctionManager functions, Listing listing,
            Function function, AddressSet body, long startOffset, long endOffset,
            boolean requireNops) throws Exception {
        Address start = toAddr(startOffset);
        Address end = toAddr(endOffset);
        Address cursor = start;
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
            if (requireNops && (!"NOP".equals(instruction.getMnemonicString()) ||
                    instruction.getLength() != 1 || instruction.getBytes()[0] != (byte)0x90)) {
                throw new IllegalStateException("expected original 0x90 NOP at " + cursor);
            }
            body.add(instruction.getMinAddress(), instruction.getMaxAddress());
            cursor = instruction.getMaxAddress().next();
        }
        if (!end.equals(cursor.previous())) {
            throw new IllegalStateException("range does not end on an instruction boundary: " + end);
        }
    }

    private void requireJump(Listing listing, long sourceOffset, long targetOffset) {
        Instruction instruction = listing.getInstructionAt(toAddr(sourceOffset));
        Address target = toAddr(targetOffset);
        if (instruction == null || !instruction.getFlowType().isJump()) {
            throw new IllegalStateException("verified jump is missing at " + toAddr(sourceOffset));
        }
        Address[] flows = instruction.getFlows();
        if (flows.length != 1 || !target.equals(flows[0])) {
            throw new IllegalStateException("jump target mismatch at " + instruction.getAddress());
        }
    }

    private long parseOffset(String value) {
        String token = value.trim();
        if (token.startsWith("0x") || token.startsWith("0X")) token = token.substring(2);
        return Long.parseUnsignedLong(token, 16);
    }
}
