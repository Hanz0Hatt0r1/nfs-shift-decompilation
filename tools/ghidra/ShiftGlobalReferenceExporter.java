// Targeted SHIFT global-reference exporter for Ghidra headless mode.
// @category SHIFT
// @menupath Tools.SHIFT.Export global references

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolTable;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

public class ShiftGlobalReferenceExporter extends GhidraScript {
    private static final String FORMAT = "SHIFT.GhidraGlobalReferences/1";

    private Listing listing;
    private Memory memory;
    private FunctionManager functions;
    private ReferenceManager references;
    private SymbolTable symbols;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "usage: ShiftGlobalReferenceExporter.java <output-jsonl> <global-address> [...]"
            );
        }

        File output = new File(args[0]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create output directory: " + parent);
        }

        listing = currentProgram.getListing();
        memory = currentProgram.getMemory();
        functions = currentProgram.getFunctionManager();
        references = currentProgram.getReferenceManager();
        symbols = currentProgram.getSymbolTable();

        List<String> missing = new ArrayList<>();
        try (PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(
            new FileOutputStream(output), StandardCharsets.UTF_8)))) {
            for (int i = 1; i < args.length && !monitor.isCancelled(); i++) {
                String token = args[i];
                Address address = parseTargetAddress(token);
                if (address == null || !memory.contains(address)) {
                    missing.add(token);
                    out.println(missingRow(token, address));
                    continue;
                }
                out.println(globalRow(token, address));
            }
        }

        if (!missing.isEmpty()) {
            throw new IllegalStateException("requested globals not found in memory: " + String.join(", ", missing));
        }
        println("SHIFT targeted global-reference export -> " + output);
    }

    private Address parseTargetAddress(String token) {
        if (token == null) return null;
        String value = token.trim();
        if (value.startsWith("DAT_") || value.startsWith("dat_")) {
            value = value.substring(4);
        }
        if (value.startsWith("0x") || value.startsWith("0X")) {
            value = value.substring(2);
        }
        try {
            long offset = Long.parseUnsignedLong(value, 16);
            return toAddr(offset);
        }
        catch (RuntimeException exc) {
            return null;
        }
    }

    private String globalRow(String requested, Address address) {
        Data data = listing.getDataAt(address);
        Symbol primary = symbols.getPrimarySymbol(address);
        LinkedHashSet<String> functionAddresses = new LinkedHashSet<>();
        StringBuilder refsJson = new StringBuilder("[");
        boolean firstRef = true;
        int refCount = 0;

        ReferenceIterator iterator = references.getReferencesTo(address);
        while (iterator.hasNext()) {
            Reference ref = iterator.next();
            refCount++;
            Address from = ref.getFromAddress();
            Function function = from == null ? null : functions.getFunctionContaining(from);
            Instruction instruction = from == null ? null : listing.getInstructionAt(from);
            if (function != null) {
                functionAddresses.add(addr(function.getEntryPoint()));
            }

            if (!firstRef) refsJson.append(',');
            firstRef = false;
            refsJson.append('{')
                .append("\"from\":").append(q(addr(from))).append(',')
                .append("\"type\":").append(q(ref.getReferenceType().getName())).append(',')
                .append("\"operand_index\":").append(ref.getOperandIndex()).append(',')
                .append("\"primary\":").append(ref.isPrimary()).append(',')
                .append("\"function_address\":")
                    .append(q(function == null ? null : addr(function.getEntryPoint()))).append(',')
                .append("\"function_name\":")
                    .append(q(function == null ? null : function.getName())).append(',')
                .append("\"instruction\":")
                    .append(q(instruction == null ? null : instruction.toString()))
                .append('}');
        }
        refsJson.append(']');

        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"program\":" + q(currentProgram.getName()) + "," +
            "\"executable_md5\":" + q(currentProgram.getExecutableMD5()) + "," +
            "\"requested\":" + q(requested) + "," +
            "\"resolved_address\":" + q(addr(address)) + "," +
            "\"found\":true," +
            "\"primary_symbol\":" + q(primary == null ? null : primary.getName(true)) + "," +
            "\"data_type\":" + q(data == null ? null : data.getDataType().getDisplayName()) + "," +
            "\"data_length\":" + (data == null ? 0 : data.getLength()) + "," +
            "\"reference_count\":" + refCount + "," +
            "\"function_addresses\":" + stringArray(functionAddresses) + "," +
            "\"references\":" + refsJson +
            "}";
    }

    private String missingRow(String requested, Address address) {
        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"program\":" + q(currentProgram.getName()) + "," +
            "\"executable_md5\":" + q(currentProgram.getExecutableMD5()) + "," +
            "\"requested\":" + q(requested) + "," +
            "\"resolved_address\":" + q(addr(address)) + "," +
            "\"found\":false," +
            "\"primary_symbol\":null," +
            "\"data_type\":null," +
            "\"data_length\":0," +
            "\"reference_count\":0," +
            "\"function_addresses\":[]," +
            "\"references\":[]" +
            "}";
    }

    private static String addr(Address address) {
        return address == null ? null : "0x" + address.toString(false, false);
    }

    private static String stringArray(Iterable<String> values) {
        StringBuilder out = new StringBuilder("[");
        boolean first = true;
        for (String value : values) {
            if (!first) out.append(',');
            first = false;
            out.append(q(value));
        }
        return out.append(']').toString();
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
        out.append('"');
        return out.toString();
    }
}
