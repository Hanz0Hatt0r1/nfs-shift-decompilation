// Export candidate instructions from functions that exhibit the proven wheel-runtime topology.
// Candidate inventory only: topology/scalar coincidence is never object identity.
// @category SHIFT
// @menupath Tools.SHIFT.Export P1A slot0/slot1 topology aliases

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.pcode.PcodeOp;
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

public class ShiftP13ASlot01TopologyAliasExporter extends GhidraScript {
    private static final String FORMAT = "SHIFT.GhidraP13ASlot01TopologyAliasCandidates/1";
    private static final long RUNTIME_BASE = 0x400L;
    private static final long STRIDE = 0xa80L;
    private static final long LOCAL_FIELD = 0x538L;
    private static final long SLOT0_ABSOLUTE = 0x938L;
    private static final long SLOT1_ABSOLUTE = 0x13b8L;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException(
                "usage: ShiftP13ASlot01TopologyAliasExporter.java <output-jsonl>"
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
            FunctionIterator iterator = functions.getFunctions(true);
            while (iterator.hasNext() && !monitor.isCancelled()) {
                Function function = iterator.next();
                FunctionScan scan = scanFunction(function, listing);
                if (scan.runtimeBaseHint && scan.strideHint) {
                    out.println(render(scan));
                    rows++;
                }
            }
        }

        println("SHIFT P1A slot0/slot1 topology alias export: " + rows + " functions -> " + output);
    }

    private static FunctionScan scanFunction(Function function, Listing listing) {
        FunctionScan scan = new FunctionScan(function);
        InstructionIterator it = listing.getInstructions(function.getBody(), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            boolean baseUse = instructionUsesScalar(ins, RUNTIME_BASE);
            boolean strideUse = instructionUsesScalar(ins, STRIDE);
            boolean localFieldUse = instructionUsesScalar(ins, LOCAL_FIELD);
            boolean slot0Use = instructionUsesScalar(ins, SLOT0_ABSOLUTE);
            boolean slot1Use = instructionUsesScalar(ins, SLOT1_ABSOLUTE);

            if (baseUse) scan.runtimeBaseHint = true;
            if (strideUse) scan.strideHint = true;
            if (localFieldUse) scan.localFieldHint = true;
            if (slot0Use) scan.slot0AbsoluteHint = true;
            if (slot1Use) scan.slot1AbsoluteHint = true;

            Set<String> pcodeOps = new LinkedHashSet<>();
            boolean interesting = false;
            for (PcodeOp op : ins.getPcode()) {
                pcodeOps.add(op.getMnemonic());
                switch (op.getOpcode()) {
                    case PcodeOp.STORE:
                        scan.hasStore = true;
                        interesting = true;
                        break;
                    case PcodeOp.LOAD:
                        scan.hasLoad = true;
                        interesting = true;
                        break;
                    case PcodeOp.CALL:
                    case PcodeOp.CALLIND:
                        scan.hasCall = true;
                        if (op.getOpcode() == PcodeOp.CALLIND) scan.hasIndirectCall = true;
                        interesting = true;
                        break;
                    case PcodeOp.COPY:
                    case PcodeOp.PIECE:
                    case PcodeOp.SUBPIECE:
                        scan.hasCopyLike = true;
                        interesting = true;
                        break;
                    case PcodeOp.PTRADD:
                    case PcodeOp.PTRSUB:
                    case PcodeOp.INT_ADD:
                    case PcodeOp.INT_MULT:
                        scan.hasAddressArithmetic = true;
                        interesting = true;
                        break;
                    default:
                        break;
                }
            }

            if (interesting || baseUse || strideUse || localFieldUse || slot0Use || slot1Use) {
                scan.events.add(new Event(
                    ins.getAddress(),
                    ins.getMnemonicString(),
                    ins.toString(),
                    baseUse,
                    strideUse,
                    localFieldUse,
                    slot0Use,
                    slot1Use,
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

    private static String render(FunctionScan scan) {
        StringBuilder events = new StringBuilder("[");
        for (int i = 0; i < scan.events.size(); i++) {
            if (i > 0) events.append(',');
            Event event = scan.events.get(i);
            events.append('{')
                .append("\"instruction_address\":").append(q(addr(event.address))).append(',')
                .append("\"mnemonic\":").append(q(event.mnemonic)).append(',')
                .append("\"text\":").append(q(event.text)).append(',')
                .append("\"runtime_base_scalar\":").append(event.runtimeBaseScalar).append(',')
                .append("\"stride_scalar\":").append(event.strideScalar).append(',')
                .append("\"local_0x538_scalar\":").append(event.localFieldScalar).append(',')
                .append("\"slot0_0x938_scalar\":").append(event.slot0Scalar).append(',')
                .append("\"slot1_0x13b8_scalar\":").append(event.slot1Scalar).append(',')
                .append("\"pcode_ops\":").append(qList(event.pcodeOps))
                .append('}');
        }
        events.append(']');

        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"program\":" + q(scan.function.getProgram().getName()) + "," +
            "\"function_address\":" + q(addr(scan.function.getEntryPoint())) + "," +
            "\"function_name\":" + q(scan.function.getName()) + "," +
            "\"runtime_base_hint\":" + scan.runtimeBaseHint + "," +
            "\"stride_hint\":" + scan.strideHint + "," +
            "\"exact_local_0x538_hint\":" + scan.localFieldHint + "," +
            "\"slot0_absolute_hint\":" + scan.slot0AbsoluteHint + "," +
            "\"slot1_absolute_hint\":" + scan.slot1AbsoluteHint + "," +
            "\"has_store\":" + scan.hasStore + "," +
            "\"has_load\":" + scan.hasLoad + "," +
            "\"has_call\":" + scan.hasCall + "," +
            "\"has_indirect_call\":" + scan.hasIndirectCall + "," +
            "\"has_copy_like\":" + scan.hasCopyLike + "," +
            "\"has_address_arithmetic\":" + scan.hasAddressArithmetic + "," +
            "\"events\":" + events +
            "}";
    }

    private static final class FunctionScan {
        final Function function;
        final List<Event> events = new ArrayList<>();
        boolean runtimeBaseHint;
        boolean strideHint;
        boolean localFieldHint;
        boolean slot0AbsoluteHint;
        boolean slot1AbsoluteHint;
        boolean hasStore;
        boolean hasLoad;
        boolean hasCall;
        boolean hasIndirectCall;
        boolean hasCopyLike;
        boolean hasAddressArithmetic;

        FunctionScan(Function function) { this.function = function; }
    }

    private static final class Event {
        final Address address;
        final String mnemonic;
        final String text;
        final boolean runtimeBaseScalar;
        final boolean strideScalar;
        final boolean localFieldScalar;
        final boolean slot0Scalar;
        final boolean slot1Scalar;
        final List<String> pcodeOps;

        Event(Address address, String mnemonic, String text, boolean runtimeBaseScalar,
                boolean strideScalar, boolean localFieldScalar, boolean slot0Scalar,
                boolean slot1Scalar, List<String> pcodeOps) {
            this.address = address;
            this.mnemonic = mnemonic;
            this.text = text;
            this.runtimeBaseScalar = runtimeBaseScalar;
            this.strideScalar = strideScalar;
            this.localFieldScalar = localFieldScalar;
            this.slot0Scalar = slot0Scalar;
            this.slot1Scalar = slot1Scalar;
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
