// Export p-code/instruction evidence around exact wheel-runtime field +0x138.
// Candidate inventory only: numeric constant equality is never object identity.
// @category SHIFT
// @menupath Tools.SHIFT.Export wheel runtime aliases

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.Varnode;
import ghidra.program.model.scalar.Scalar;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class ShiftWheelRuntimeAliasExporter extends GhidraScript {
    private static final String FORMAT = "SHIFT.GhidraWheelRuntimeAliasUses/1";
    private static final long FIELD = 0x138L;
    private static final long RUNTIME_BASE = 0x400L;
    private static final long STRIDE = 0xa80L;
    private static final long SLOT3_ABSOLUTE = 0x28b8L;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException(
                "usage: ShiftWheelRuntimeAliasExporter.java <output-jsonl>"
            );
        }

        File output = new File(args[0]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create output directory: " + parent);
        }

        Listing listing = currentProgram.getListing();
        FunctionManager functions = currentProgram.getFunctionManager();
        int rows = 0;

        try (PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(output), StandardCharsets.UTF_8)))) {
            Function function = functions.getFirstFunction();
            while (function != null && !monitor.isCancelled()) {
                FunctionScan scan = scanFunction(function, listing);
                if (scan.fieldUseCount > 0) {
                    out.println(render(scan));
                    rows++;
                }
                function = functions.getFunctionAfter(function);
            }
        }

        println("SHIFT wheel-runtime alias export: " + rows + " functions -> " + output);
    }

    private static FunctionScan scanFunction(Function function, Listing listing) {
        FunctionScan scan = new FunctionScan(function);
        InstructionIterator it = listing.getInstructions(function.getBody(), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            boolean fieldUse = instructionUsesScalar(ins, FIELD);
            boolean baseUse = instructionUsesScalar(ins, RUNTIME_BASE);
            boolean strideUse = instructionUsesScalar(ins, STRIDE);
            boolean absoluteUse = instructionUsesScalar(ins, SLOT3_ABSOLUTE);

            if (baseUse) scan.runtimeBaseHint = true;
            if (strideUse) scan.strideHint = true;
            if (absoluteUse) scan.slot3AbsoluteHint = true;

            PcodeOp[] pcode = ins.getPcode();
            boolean pcodeFieldUse = false;
            Set<String> pcodeOps = new LinkedHashSet<>();
            for (PcodeOp op : pcode) {
                pcodeOps.add(op.getMnemonic());
                if (pcodeUsesConstant(op, FIELD)) pcodeFieldUse = true;
                if (op.getOpcode() == PcodeOp.STORE) scan.hasStore = true;
                if (op.getOpcode() == PcodeOp.LOAD) scan.hasLoad = true;
                if (op.getOpcode() == PcodeOp.CALL || op.getOpcode() == PcodeOp.CALLIND) {
                    scan.hasCall = true;
                    if (op.getOpcode() == PcodeOp.CALLIND) scan.hasIndirectCall = true;
                }
                if (op.getOpcode() == PcodeOp.COPY || op.getOpcode() == PcodeOp.PIECE || op.getOpcode() == PcodeOp.SUBPIECE) {
                    scan.hasCopyLike = true;
                }
                if (op.getOpcode() == PcodeOp.PTRADD || op.getOpcode() == PcodeOp.PTRSUB ||
                    op.getOpcode() == PcodeOp.INT_ADD || op.getOpcode() == PcodeOp.INT_MULT) {
                    scan.hasAddressArithmetic = true;
                }
            }

            if (fieldUse || pcodeFieldUse) {
                scan.fieldUseCount++;
                scan.uses.add(new Use(
                    ins.getAddress(),
                    ins.getMnemonicString(),
                    ins.toString(),
                    fieldUse,
                    pcodeFieldUse,
                    new ArrayList<>(pcodeOps)
                ));
            }
        }
        return scan;
    }

    private static boolean instructionUsesScalar(Instruction ins, long target) {
        for (int i = 0; i < ins.getNumOperands(); i++) {
            for (Object object : ins.getOpObjects(i)) {
                if (!(object instanceof Scalar)) continue;
                Scalar scalar = (Scalar) object;
                if (Long.compareUnsigned(scalar.getUnsignedValue(), target) == 0) return true;
            }
        }
        return false;
    }

    private static boolean pcodeUsesConstant(PcodeOp op, long target) {
        for (int i = 0; i < op.getNumInputs(); i++) {
            Varnode input = op.getInput(i);
            if (input == null || !input.isConstant()) continue;
            if (Long.compareUnsigned(input.getOffset(), target) == 0) return true;
        }
        return false;
    }

    private static String render(FunctionScan scan) {
        StringBuilder uses = new StringBuilder();
        uses.append('[');
        for (int i = 0; i < scan.uses.size(); i++) {
            if (i > 0) uses.append(',');
            Use use = scan.uses.get(i);
            uses.append('{')
                .append("\"instruction_address\":").append(q(addr(use.address))).append(',')
                .append("\"mnemonic\":").append(q(use.mnemonic)).append(',')
                .append("\"text\":").append(q(use.text)).append(',')
                .append("\"instruction_scalar_match\":").append(use.instructionScalarMatch).append(',')
                .append("\"pcode_constant_match\":").append(use.pcodeConstantMatch).append(',')
                .append("\"pcode_ops\":").append(qList(use.pcodeOps))
                .append('}');
        }
        uses.append(']');

        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"program\":" + q(scan.function.getProgram().getName()) + "," +
            "\"function_address\":" + q(addr(scan.function.getEntryPoint())) + "," +
            "\"function_name\":" + q(scan.function.getName()) + "," +
            "\"field_offset\":\"0x138\"," +
            "\"runtime_base_hint\":" + scan.runtimeBaseHint + "," +
            "\"stride_hint\":" + scan.strideHint + "," +
            "\"slot3_absolute_hint\":" + scan.slot3AbsoluteHint + "," +
            "\"field_use_count\":" + scan.fieldUseCount + "," +
            "\"has_store\":" + scan.hasStore + "," +
            "\"has_load\":" + scan.hasLoad + "," +
            "\"has_call\":" + scan.hasCall + "," +
            "\"has_indirect_call\":" + scan.hasIndirectCall + "," +
            "\"has_copy_like\":" + scan.hasCopyLike + "," +
            "\"has_address_arithmetic\":" + scan.hasAddressArithmetic + "," +
            "\"uses\":" + uses +
            "}";
    }

    private static final class FunctionScan {
        final Function function;
        final List<Use> uses = new ArrayList<>();
        int fieldUseCount = 0;
        boolean runtimeBaseHint = false;
        boolean strideHint = false;
        boolean slot3AbsoluteHint = false;
        boolean hasStore = false;
        boolean hasLoad = false;
        boolean hasCall = false;
        boolean hasIndirectCall = false;
        boolean hasCopyLike = false;
        boolean hasAddressArithmetic = false;

        FunctionScan(Function function) { this.function = function; }
    }

    private static final class Use {
        final Address address;
        final String mnemonic;
        final String text;
        final boolean instructionScalarMatch;
        final boolean pcodeConstantMatch;
        final List<String> pcodeOps;

        Use(Address address, String mnemonic, String text, boolean instructionScalarMatch,
                boolean pcodeConstantMatch, List<String> pcodeOps) {
            this.address = address;
            this.mnemonic = mnemonic;
            this.text = text;
            this.instructionScalarMatch = instructionScalarMatch;
            this.pcodeConstantMatch = pcodeConstantMatch;
            this.pcodeOps = pcodeOps;
        }
    }

    private static String qList(List<String> values) {
        StringBuilder out = new StringBuilder("[");
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) out.append(',');
            out.append(q(values.get(i)));
        }
        return out.append(']').toString();
    }

    private static String addr(Address address) {
        return address == null ? null : "0x" + address.toString(false, false);
    }

    private static String q(String value) {
        if (value == null) return "null";
        StringBuilder out = new StringBuilder(value.length() + 16);
        out.append('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '\\': out.append("\\\\"); break;
                case '"': out.append("\\\""); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 0x20) out.append(String.format("\\u%04x", (int)c));
                    else out.append(c);
            }
        }
        return out.append('"').toString();
    }
}
