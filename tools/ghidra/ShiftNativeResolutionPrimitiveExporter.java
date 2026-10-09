// Export x86 machine primitives relevant to manual API resolution and direct native calls.
// @category SHIFT
// @menupath Tools.SHIFT.Export native resolution primitives

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

public class ShiftNativeResolutionPrimitiveExporter extends GhidraScript {
    private static final String FORMAT = "SHIFT.GhidraNativeResolutionPrimitiveInventory/1";

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException(
                "usage: ShiftNativeResolutionPrimitiveExporter.java <output-jsonl>"
            );
        }

        File output = new File(args[0]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create output directory: " + parent);
        }

        Listing listing = currentProgram.getListing();
        FunctionManager functions = currentProgram.getFunctionManager();
        long emitted = 0;

        try (PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(
            new FileOutputStream(output), StandardCharsets.UTF_8)))) {
            for (Function function : functions.getFunctions(true)) {
                if (monitor.isCancelled()) break;
                InstructionIterator it = listing.getInstructions(function.getBody(), true);
                while (it.hasNext()) {
                    Instruction ins = it.next();
                    String text = ins.toString();
                    String lower = text.toLowerCase(Locale.ROOT);
                    String mnemonic = ins.getMnemonicString().toLowerCase(Locale.ROOT);

                    boolean fsAccess = lower.contains("fs:") || lower.contains("fs[") || lower.contains("fs:[");
                    boolean sysenter = mnemonic.equals("sysenter");
                    boolean int2e = mnemonic.equals("int") && (lower.contains("0x2e") || lower.matches(".*\\b2eh\\b.*"));
                    boolean exportOffset = containsExportOffset(lower);
                    if (!(fsAccess || sysenter || int2e || exportOffset)) continue;

                    out.println("{" +
                        "\"format\":" + q(FORMAT) + "," +
                        "\"program\":" + q(currentProgram.getName()) + "," +
                        "\"function\":" + q(function.getName()) + "," +
                        "\"function_address\":" + q(addr(function.getEntryPoint().getOffset())) + "," +
                        "\"address\":" + q(addr(ins.getAddress().getOffset())) + "," +
                        "\"mnemonic\":" + q(ins.getMnemonicString()) + "," +
                        "\"text\":" + q(text) + "," +
                        "\"fs_access\":" + fsAccess + "," +
                        "\"sysenter\":" + sysenter + "," +
                        "\"int2e\":" + int2e + "," +
                        "\"export_offset_hint\":" + exportOffset +
                        "}");
                    emitted++;
                }
            }
        }

        println("SHIFT native-resolution primitive inventory -> " + output + " (" + emitted + " rows)");
    }

    private static boolean containsExportOffset(String lower) {
        // Navigation hints only. These are common x86 PE/PEB export-walk constants and
        // never become semantic proof without local receiver/data-flow adjudication.
        String[] tokens = {
            "0x30", "30h",   // x86 PEB through FS:[0x30]
            "0x0c", "0ch",   // PEB_LDR_DATA link
            "0x14", "14h",   // loader list family
            "0x1c", "1ch", "0x20", "20h", "0x24", "24h", // export arrays
            "0x3c", "3ch",   // DOS e_lfanew
            "0x78", "78h"    // PE32 export directory RVA
        };
        for (String token : tokens) {
            if (lower.contains(token)) return true;
        }
        return false;
    }

    private static String addr(long value) {
        return String.format("0x%08x", value);
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
