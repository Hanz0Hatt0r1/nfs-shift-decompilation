// Export one compact whole-program instruction stream for Process 1 retail frontier runners.
// The first JSONL row is an identity header; remaining rows are instructions.
// Files ending in .gz are gzip-compressed.
// @category SHIFT
// @menupath Tools.SHIFT.Export compact instruction stream

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;

import java.io.BufferedOutputStream;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.zip.GZIPOutputStream;

public class ShiftCompactInstructionStreamExporter extends GhidraScript {
    private static final String FORMAT = "SHIFT.GhidraCompactInstructionStream/1";

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException(
                "usage: ShiftCompactInstructionStreamExporter.java <output-jsonl[.gz]>"
            );
        }

        File output = new File(args[0]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create output directory: " + parent);
        }

        Listing listing = currentProgram.getListing();
        long count = 0;
        try (OutputStream raw = new BufferedOutputStream(new FileOutputStream(output));
             OutputStream encoded = output.getName().endsWith(".gz") ? new GZIPOutputStream(raw) : raw;
             PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(encoded, StandardCharsets.UTF_8)))) {
            out.println(headerRow());
            InstructionIterator iterator = listing.getInstructions(true);
            while (iterator.hasNext() && !monitor.isCancelled()) {
                out.println(instructionRow(iterator.next()));
                count++;
                if ((count & 0xffffL) == 0) {
                    monitor.setMessage("SHIFT compact instruction export: " + count + " instructions");
                }
            }
        }
        println("SHIFT compact instruction stream: " + count + " rows -> " + output);
    }

    private String headerRow() {
        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"kind\":\"header\"," +
            "\"program\":" + q(currentProgram.getName()) + "," +
            "\"executable_md5\":" + q(currentProgram.getExecutableMD5()) + "," +
            "\"language_id\":" + q(currentProgram.getLanguageID().toString()) + "," +
            "\"image_base\":" + q(addr(currentProgram.getImageBase())) + "," +
            "\"pointer_size\":" + currentProgram.getDefaultPointerSize() +
            "}";
    }

    private String instructionRow(Instruction instruction) {
        StringBuilder operands = new StringBuilder("[");
        for (int index = 0; index < instruction.getNumOperands(); index++) {
            if (index > 0) operands.append(',');
            operands.append(q(instruction.getDefaultOperandRepresentation(index)));
        }
        operands.append(']');

        Address[] flowAddresses = instruction.getFlows();
        StringBuilder flows = new StringBuilder("[");
        for (int index = 0; index < flowAddresses.length; index++) {
            if (index > 0) flows.append(',');
            flows.append(q(addr(flowAddresses[index])));
        }
        flows.append(']');

        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"kind\":\"instruction\"," +
            "\"address\":" + q(addr(instruction.getAddress())) + "," +
            "\"mnemonic\":" + q(instruction.getMnemonicString()) + "," +
            "\"operands\":" + operands + "," +
            "\"flow_type\":" + q(instruction.getFlowType().toString()) + "," +
            "\"flows\":" + flows +
            "}";
    }

    private static String addr(Address address) {
        return address == null ? null : "0x" + address.toString(false, false);
    }

    private static String q(String value) {
        if (value == null) return "null";
        StringBuilder out = new StringBuilder(value.length() + 16).append('"');
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
