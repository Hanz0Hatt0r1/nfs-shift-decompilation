// Define the verified callback target at 0x007bf2c0.
//@category SHIFT.Recovery

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.SourceType;

public class DefineShiftFunctionBody007BF2C0 extends GhidraScript {
    private static final long ENTRY = 0x007bf2c0L;
    private static final long RETURN = 0x007bf308L;
    private static final long PADDING_END = 0x007bf30fL;

    @Override
    public void run() throws Exception {
        FunctionManager functions = currentProgram.getFunctionManager();
        Listing listing = currentProgram.getListing();
        Memory memory = currentProgram.getMemory();
        Address entry = toAddr(ENTRY);
        Address end = toAddr(RETURN);

        if (functions.getFunctionAt(entry) != null ||
                functions.getFunctionContaining(entry) != null) {
            throw new IllegalStateException("0x007bf2c0 already belongs to a function");
        }
        requireBytes(memory, ENTRY, "d9ee");
        requireBytes(memory, 0x007bf2c2L, "8bc1");
        requireBytes(memory, 0x007bf2c4L, "dd5038");
        requireBytes(memory, 0x007bf2caL, "d9e8");
        requireBytes(memory, 0x007bf2d2L, "dd5008");
        requireBytes(memory, 0x007bf305L, "dd5858");
        requireBytes(memory, RETURN, "c3");
        requireBytes(memory, 0x007bf309L, "cccccccccccccc");

        int transaction = currentProgram.startTransaction("Define verified FUN_007bf2c0");
        boolean commit = false;
        try {
            Address cursor = entry;
            Instruction last = null;
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
                if (owner != null) {
                    throw new IllegalStateException("range overlaps function " + owner.getEntryPoint());
                }
                last = instruction;
                cursor = instruction.getMaxAddress().next();
            }
            if (last == null || last.getMaxAddress().getOffset() != RETURN ||
                    !last.getFlowType().isTerminal() || cursor.getOffset() != RETURN + 1) {
                throw new IllegalStateException("0x007bf308 must be the terminal body instruction");
            }

            AddressSet body = new AddressSet(entry, end);
            Function function = functions.createFunction(
                    "FUN_007bf2c0", entry, body, SourceType.USER_DEFINED);
            if (function == null) {
                throw new IllegalStateException("Ghidra did not create FUN_007bf2c0");
            }
            function.setCallingConvention("__thiscall");
            if (function.getBody().getNumAddresses() != 73 ||
                    function.getBody().contains(toAddr(RETURN + 1)) ||
                    function.getBody().contains(toAddr(PADDING_END)) ||
                    !"__thiscall".equals(function.getCallingConventionName())) {
                throw new IllegalStateException("function body or calling convention is unexpected");
            }
            commit = true;
            println("Defined FUN_007bf2c0 through verified RET; body bytes=" +
                    function.getBody().getNumAddresses());
        }
        finally {
            currentProgram.endTransaction(transaction, commit);
        }
    }

    private void requireBytes(Memory memory, long address, String expected) throws Exception {
        byte[] bytes = new byte[expected.length() / 2];
        memory.getBytes(toAddr(address), bytes);
        if (!expected.equals(hex(bytes))) {
            throw new IllegalStateException("retail byte mismatch at " + toAddr(address));
        }
    }

    private String hex(byte[] bytes) {
        StringBuilder value = new StringBuilder(bytes.length * 2);
        for (byte item : bytes) value.append(String.format("%02x", item & 0xff));
        return value.toString();
    }
}
