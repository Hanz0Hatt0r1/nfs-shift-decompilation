// Export candidate persistence/escape uses of machine-proven exact wheel-root registers.
// Candidate inventory only: register mention or data-flow proximity is not semantic persistence proof.
// @category SHIFT
// @menupath Tools.SHIFT.Export exact wheel-root persistence frontier

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.pcode.PcodeOp;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

public class ShiftExactWheelRootPersistenceExporter extends GhidraScript {
    private static final String FORMAT = "SHIFT.GhidraExactWheelRootPersistenceUses/1";

    // These windows come only from already-merged retail machine contracts. They bound
    // where the listed register is known to carry the exact wheel root. This exporter
    // does not discover or extend semantic root lifetimes by itself.
    private static final RootWindow[] WINDOWS = new RootWindow[] {
        new RootWindow(0x00758b50L, "FUN_00758b50", "ecx", 0x00758ccfL, 0x00758d70L,
            "ECX materialized as HDVehicle+0x400+slot*0xa80 before FUN_00755950"),
        new RootWindow(0x00755950L, "FUN_00755950", "edx", 0x00755956L, 0x00755992L,
            "EDX=entry ECX exact wheel root"),
        new RootWindow(0x00755a60L, "FUN_00755a60", "esi", 0x00755a73L, 0x00755f71L,
            "ESI=entry ECX exact wheel root"),
        new RootWindow(0x00752fc0L, "FUN_00752fc0", "ecx", 0x00752fc0L, 0x00752fe5L,
            "entry ECX exact wheel root"),
        new RootWindow(0x00760b50L, "FUN_00760b50", "esi", 0x00760b6aL, 0x00760d63L,
            "ESI=entry ECX exact wheel root"),
        new RootWindow(0x00755f80L, "FUN_00755f80", "esi", 0x00755f80L, 0x00756004L,
            "ESI captures entry ECX exact wheel root")
    };

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException(
                "usage: ShiftExactWheelRootPersistenceExporter.java <output-jsonl>"
            );
        }

        File output = new File(args[0]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create output directory: " + parent);
        }

        Listing listing = currentProgram.getListing();
        FunctionManager functions = currentProgram.getFunctionManager();
        int emitted = 0;

        try (PrintWriter out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(output), StandardCharsets.UTF_8)))) {
            for (RootWindow window : WINDOWS) {
                if (monitor.isCancelled()) break;
                Function function = functions.getFunctionAt(toAddr(window.functionAddress));
                if (function == null) {
                    throw new IllegalStateException("missing function at " + hex(window.functionAddress));
                }
                if (!window.functionName.equals(function.getName())) {
                    throw new IllegalStateException(
                        "function identity drift at " + hex(window.functionAddress) +
                        ": " + function.getName()
                    );
                }
                FunctionScan scan = scanFunction(function, window, listing);
                out.println(render(scan));
                emitted++;
            }
        }

        println("SHIFT exact wheel-root persistence export: " + emitted + " carrier windows -> " + output);
    }

    private static FunctionScan scanFunction(Function function, RootWindow window, Listing listing) {
        FunctionScan scan = new FunctionScan(function, window);
        Pattern rootWord = Pattern.compile("(?i)(?<![a-z0-9_])" + Pattern.quote(window.rootRegister) + "(?![a-z0-9_])");
        InstructionIterator it = listing.getInstructions(function.getBody(), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            long offset = ins.getAddress().getOffset();
            if (Long.compareUnsigned(offset, window.startAddress) < 0 ||
                    Long.compareUnsigned(offset, window.endAddress) >= 0) {
                continue;
            }

            String text = ins.toString();
            String lower = text.toLowerCase(Locale.ROOT).trim();
            String mnemonic = ins.getMnemonicString().toLowerCase(Locale.ROOT);
            boolean rootMention = rootWord.matcher(lower).find();
            boolean call = mnemonic.startsWith("call");
            if (!rootMention && !call) continue;

            List<String> kinds = classify(lower, mnemonic, window.rootRegister, rootMention, call);
            List<String> pcodeOps = new ArrayList<>();
            for (PcodeOp op : ins.getPcode()) {
                pcodeOps.add(op.getMnemonic());
            }
            scan.uses.add(new Use(ins.getAddress(), mnemonic, text, rootMention, kinds, pcodeOps));
            if (rootMention) scan.rootMentionCount++;
            if (call) scan.callBoundaryCount++;
            if (kinds.contains("memory-store-root")) scan.memoryStoreRootCount++;
            if (kinds.contains("push-root")) scan.pushRootCount++;
            if (kinds.contains("register-copy-root")) scan.registerCopyRootCount++;
            if (kinds.contains("derived-address-root")) scan.derivedAddressRootCount++;
        }
        return scan;
    }

    private static List<String> classify(String text, String mnemonic, String root, boolean rootMention, boolean call) {
        List<String> kinds = new ArrayList<>();
        if (call) kinds.add("call-boundary");
        if (!rootMention) return kinds;

        String[] operands = splitOperands(text, mnemonic);
        String dst = operands[0];
        String src = operands[1];
        Pattern rootWord = Pattern.compile("(?i)(?<![a-z0-9_])" + Pattern.quote(root) + "(?![a-z0-9_])");
        boolean srcIsRoot = rootWord.matcher(src).find();
        boolean dstMentionsRoot = rootWord.matcher(dst).find();

        if (mnemonic.equals("push") && dstMentionsRoot) kinds.add("push-root");
        if ((mnemonic.startsWith("mov") || mnemonic.equals("xchg")) && dst.contains("[") && srcIsRoot) {
            kinds.add("memory-store-root");
        }
        if (mnemonic.startsWith("mov") && !dst.contains("[") && srcIsRoot) {
            kinds.add("register-copy-root");
        }
        if (mnemonic.equals("lea") && src.contains("[") && srcIsRoot) {
            kinds.add("derived-address-root");
        }
        if (dst.contains("[") && dstMentionsRoot && !kinds.contains("memory-store-root")) {
            kinds.add("root-based-memory-destination");
        }
        if (src.contains("[") && srcIsRoot) kinds.add("root-based-memory-source");
        if (kinds.isEmpty()) kinds.add("other-root-use");
        return kinds;
    }

    private static String[] splitOperands(String text, String mnemonic) {
        String body = text.trim();
        if (body.length() >= mnemonic.length() && body.substring(0, mnemonic.length()).equalsIgnoreCase(mnemonic)) {
            body = body.substring(mnemonic.length()).trim();
        }
        int comma = body.indexOf(',');
        if (comma < 0) return new String[] { body.toLowerCase(Locale.ROOT), "" };
        return new String[] {
            body.substring(0, comma).trim().toLowerCase(Locale.ROOT),
            body.substring(comma + 1).trim().toLowerCase(Locale.ROOT)
        };
    }

    private static String render(FunctionScan scan) {
        StringBuilder uses = new StringBuilder("[");
        for (int i = 0; i < scan.uses.size(); i++) {
            if (i > 0) uses.append(',');
            Use use = scan.uses.get(i);
            uses.append('{')
                .append("\"instruction_address\":").append(q(addr(use.address))).append(',')
                .append("\"mnemonic\":").append(q(use.mnemonic)).append(',')
                .append("\"text\":").append(q(use.text)).append(',')
                .append("\"exact_root_register_mentioned\":").append(use.rootMention).append(',')
                .append("\"candidate_kinds\":").append(qList(use.kinds)).append(',')
                .append("\"pcode_ops\":").append(qList(use.pcodeOps))
                .append('}');
        }
        uses.append(']');

        return "{" +
            "\"format\":" + q(FORMAT) + "," +
            "\"program\":" + q(scan.function.getProgram().getName()) + "," +
            "\"function_address\":" + q(hex(scan.window.functionAddress)) + "," +
            "\"function_name\":" + q(scan.window.functionName) + "," +
            "\"root_register\":" + q(scan.window.rootRegister) + "," +
            "\"window_start\":" + q(hex(scan.window.startAddress)) + "," +
            "\"window_end_exclusive\":" + q(hex(scan.window.endAddress)) + "," +
            "\"identity_note\":" + q(scan.window.identityNote) + "," +
            "\"root_mention_count\":" + scan.rootMentionCount + "," +
            "\"call_boundary_count\":" + scan.callBoundaryCount + "," +
            "\"memory_store_root_count\":" + scan.memoryStoreRootCount + "," +
            "\"push_root_count\":" + scan.pushRootCount + "," +
            "\"register_copy_root_count\":" + scan.registerCopyRootCount + "," +
            "\"derived_address_root_count\":" + scan.derivedAddressRootCount + "," +
            "\"uses\":" + uses +
            "}";
    }

    private static final class RootWindow {
        final long functionAddress;
        final String functionName;
        final String rootRegister;
        final long startAddress;
        final long endAddress;
        final String identityNote;

        RootWindow(long functionAddress, String functionName, String rootRegister,
                long startAddress, long endAddress, String identityNote) {
            this.functionAddress = functionAddress;
            this.functionName = functionName;
            this.rootRegister = rootRegister;
            this.startAddress = startAddress;
            this.endAddress = endAddress;
            this.identityNote = identityNote;
        }
    }

    private static final class FunctionScan {
        final Function function;
        final RootWindow window;
        final List<Use> uses = new ArrayList<>();
        int rootMentionCount;
        int callBoundaryCount;
        int memoryStoreRootCount;
        int pushRootCount;
        int registerCopyRootCount;
        int derivedAddressRootCount;

        FunctionScan(Function function, RootWindow window) {
            this.function = function;
            this.window = window;
        }
    }

    private static final class Use {
        final Address address;
        final String mnemonic;
        final String text;
        final boolean rootMention;
        final List<String> kinds;
        final List<String> pcodeOps;

        Use(Address address, String mnemonic, String text, boolean rootMention,
                List<String> kinds, List<String> pcodeOps) {
            this.address = address;
            this.mnemonic = mnemonic;
            this.text = text;
            this.rootMention = rootMention;
            this.kinds = kinds;
            this.pcodeOps = pcodeOps;
        }
    }

    private static String addr(Address address) {
        return address == null ? null : "0x" + address.toString(false, false);
    }

    private static String hex(long value) {
        return String.format("0x%08x", value);
    }

    private static String qList(List<String> values) {
        StringBuilder out = new StringBuilder("[");
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) out.append(',');
            out.append(q(values.get(i)));
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
        return out.append('"').toString();
    }
}
