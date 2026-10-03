// Targeted SHIFT function instruction exporter for Ghidra headless mode.
// @category SHIFT
// @menupath Tools.SHIFT.Export function instructions

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.MemoryAccessException;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.symbol.Reference;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class ShiftFunctionInstructionExporter extends GhidraScript {
    private static final String FORMAT = "SHIFT.GhidraFunctionInstructions/2";

    private Listing listing;
    private FunctionManager functions;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "usage: ShiftFunctionInstructionExporter.java <output-jsonl> <function-address> [...]"
            );
        }

        File output = new File(args[0]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create output directory: " + parent);
        }

        listing = currentProgram.getListing();
        functions = currentProgram.getFunctionManager();

        List<String> missing = new ArrayList<>();
        try (PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(
            new FileOutputStream(output), StandardCharsets.UTF_8)))) {
            for (int i = 1; i < args.length && !monitor.isCancelled(); i++) {
                String token = args[i];
                Address address = parseTargetAddress(token);
                Function function = address == null ? null : functions.getFunctionAt(address);
                if (function == null) {
                    missing.add(token);
                    out.println(missingRow(token, address));
                    continue;
                }
                out.println(functionRow(function));
            }
        }

        if (!missing.isEmpty()) {
            throw new IllegalStateException("requested functions not found: " + String.join(", ", missing));
        }
        println("SHIFT targeted instruction export -> " + output);
    }

    // Do not name this parseAddress: GhidraScript already exposes a public
    // parseAddress(String), and a private method with that signature is an illegal
    // weaker-access override on Ghidra 12.1.x.
    private Address parseTargetAddress(String token) {
        if (token == null) return null;
        String value = token.trim();
        if (value.startsWith("FUN_") || value.startsWith("fun_")) {
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

    private String functionRow(Function function) throws MemoryAccessException {
        StringBuilder instructions = new StringBuilder("[");
        boolean first = true;
        int instructionCount = 0;
        InstructionIterator iterator = listing.getInstructions(function.getBody(), true);
        while (iterator.hasNext()) {
            Instruction instruction = iterator.next();
            if (!first) instructions.append(',');
            first = false;
            instructions.append(instructionJson(instruction));
            instructionCount++;
        }
        instructions.append(']');

        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"program\":" + q(currentProgram.getName()) + "," +
            "\"requested\":" + q(addr(function.getEntryPoint())) + "," +
            "\"found\":true," +
            "\"function\":{" +
                "\"address\":" + q(addr(function.getEntryPoint())) + "," +
                "\"name\":" + q(function.getName()) + "," +
                "\"size\":" + function.getBody().getNumAddresses() + "," +
                "\"calling_convention\":" + q(function.getCallingConventionName()) +
            "}," +
            "\"instruction_count\":" + instructionCount + "," +
            "\"instructions\":" + instructions +
            "}";
    }

    private String missingRow(String token, Address address) {
        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"program\":" + q(currentProgram.getName()) + "," +
            "\"requested\":" + q(token) + "," +
            "\"resolved_address\":" + q(addr(address)) + "," +
            "\"found\":false," +
            "\"function\":null," +
            "\"instruction_count\":0," +
            "\"instructions\":[]" +
            "}";
    }

    private String instructionJson(Instruction instruction) throws MemoryAccessException {
        StringBuilder operands = new StringBuilder("[");
        for (int index = 0; index < instruction.getNumOperands(); index++) {
            if (index > 0) operands.append(',');
            operands.append(q(instruction.getDefaultOperandRepresentation(index)));
        }
        operands.append(']');

        StringBuilder refs = new StringBuilder("[");
        boolean firstRef = true;
        for (Reference ref : instruction.getReferencesFrom()) {
            if (!firstRef) refs.append(',');
            firstRef = false;
            refs.append('{')
                .append("\"to\":").append(q(addr(ref.getToAddress()))).append(',')
                .append("\"type\":").append(q(ref.getReferenceType().getName()))
                .append('}');
        }
        refs.append(']');

        StringBuilder flows = new StringBuilder("[");
        Address[] flowAddresses = instruction.getFlows();
        for (int index = 0; index < flowAddresses.length; index++) {
            if (index > 0) flows.append(',');
            flows.append(q(addr(flowAddresses[index])));
        }
        flows.append(']');

        StringBuilder pcode = new StringBuilder("[");
        PcodeOp[] pcodeOps = instruction.getPcode();
        for (int index = 0; index < pcodeOps.length; index++) {
            if (index > 0) pcode.append(',');
            pcode.append(q(pcodeOps[index].toString()));
        }
        pcode.append(']');

        return "{" +
            "\"address\":" + q(addr(instruction.getAddress())) + "," +
            "\"bytes\":" + q(hex(instruction.getBytes())) + "," +
            "\"mnemonic\":" + q(instruction.getMnemonicString()) + "," +
            "\"text\":" + q(instruction.toString()) + "," +
            "\"operands\":" + operands + "," +
            "\"flow_type\":" + q(instruction.getFlowType().toString()) + "," +
            "\"fallthrough\":" + q(addr(instruction.getFallThrough())) + "," +
            "\"flows\":" + flows + "," +
            "\"references\":" + refs + "," +
            "\"pcode\":" + pcode +
            "}";
    }

    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) {
            out.append(String.format("%02x", value & 0xff));
        }
        return out.toString();
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
        out.append('"');
        return out.toString();
    }
}
