// Define a bounded SHIFT function range after its entry and terminal boundary are verified.
//@category SHIFT.Recovery

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.SourceType;

public class DefineShiftFunctionRange extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException(
                "Usage: DefineShiftFunctionRange.java <entry> <inclusive-end>");
        }
        Address entry = toAddr(parseOffset(args[0]));
        Address end = toAddr(parseOffset(args[1]));
        if (end.compareTo(entry) < 0) throw new IllegalArgumentException("end precedes entry");

        int transaction = currentProgram.startTransaction("Define verified SHIFT function range");
        boolean commit = false;
        try {
            Listing listing = currentProgram.getListing();
            FunctionManager functions = currentProgram.getFunctionManager();
            Function atEntry = functions.getFunctionAt(entry);
            Function owner = functions.getFunctionContaining(entry);
            if (atEntry == null && owner != null) {
                throw new IllegalStateException("entry is already inside " + owner.getEntryPoint());
            }

            Address cursor = entry;
            Instruction last = null;
            while (cursor.compareTo(end) <= 0) {
                Instruction instruction = listing.getInstructionAt(cursor);
                if (instruction == null) {
                    disassemble(cursor);
                    instruction = listing.getInstructionAt(cursor);
                }
                if (instruction == null || instruction.getMaxAddress().compareTo(end) > 0) {
                    throw new IllegalStateException("instruction coverage has a gap at " + cursor);
                }
                Function instructionOwner = functions.getFunctionContaining(cursor);
                if (instructionOwner != null && instructionOwner != atEntry) {
                    throw new IllegalStateException(
                        "range overlaps existing function " + instructionOwner.getEntryPoint());
                }
                if (cursor.equals(end) || instruction.getMaxAddress().equals(end)) last = instruction;
                cursor = instruction.getMaxAddress().next();
            }
            boolean terminal = last != null &&
                (last.getFlowType().isTerminal() ||
                 (last.getFlowType().isJump() && last.getFallThrough() == null));
            if (last == null || !last.getMaxAddress().equals(end) || !terminal) {
                throw new IllegalStateException("inclusive end must be the final byte of a terminal instruction");
            }

            AddressSet body = new AddressSet(entry, end);
            Function function = atEntry;
            if (function == null) {
                String name = "FUN_" + String.format("%08x", entry.getOffset());
                function = functions.createFunction(name, entry, body, SourceType.USER_DEFINED);
            }
            if (function == null || !entry.equals(function.getBody().getMinAddress())
                    || !end.equals(function.getBody().getMaxAddress())
                    || function.getBody().getNumAddresses() != end.subtract(entry) + 1) {
                throw new IllegalStateException("Ghidra did not create the exact requested body");
            }
            commit = true;
            println("Defined verified function range " + entry + ".." + end
                + " (" + function.getBody().getNumAddresses() + " bytes)");
        }
        finally {
            currentProgram.endTransaction(transaction, commit);
        }
    }

    private long parseOffset(String value) {
        String token = value.trim();
        if (token.startsWith("0x") || token.startsWith("0X")) token = token.substring(2);
        return Long.parseUnsignedLong(token, 16);
    }
}
