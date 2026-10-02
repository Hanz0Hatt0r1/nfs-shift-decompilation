// SHIFT evidence exporter for Ghidra headless mode.
// @category SHIFT
// @menupath Tools.SHIFT.Export evidence database

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.Array;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.Pointer;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryAccessException;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.program.model.symbol.SymbolType;
import ghidra.program.util.DefinedDataIterator;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class ShiftEvidenceExporter extends GhidraScript {
    private static final String FORMAT = "SHIFT.GhidraEvidenceDatabase/1";
    private static final int MAX_RAW_DATA_BYTES = 4096;
    private static final int MAX_INSTRUCTION_PREVIEW = 160;
    private static final int MIN_VTABLE_FUNCTIONS = 3;

    private File outputDir;
    private Listing listing;
    private Memory memory;
    private FunctionManager functions;
    private ReferenceManager references;
    private final Map<String, LinkedHashSet<String>> stringsByFunction = new HashMap<>();
    private final Map<String, LinkedHashSet<String>> callsByFunction = new HashMap<>();
    private final List<VtableCandidate> vtables = new ArrayList<>();
    private final Map<String, LinkedHashSet<String>> vtablesByFunction = new HashMap<>();
    private final Map<String, Integer> counts = new LinkedHashMap<>();

    private static class VtableCandidate {
        Address address;
        String block;
        List<Address> targets = new ArrayList<>();
        List<String> users = new ArrayList<>();
    }

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1 || args[0].trim().isEmpty()) {
            throw new IllegalArgumentException("usage: ShiftEvidenceExporter.java <output-directory>");
        }

        outputDir = new File(args[0]).getAbsoluteFile();
        if (!outputDir.exists() && !outputDir.mkdirs()) {
            throw new IllegalStateException("cannot create output directory: " + outputDir);
        }

        listing = currentProgram.getListing();
        memory = currentProgram.getMemory();
        functions = currentProgram.getFunctionManager();
        references = currentProgram.getReferenceManager();

        println("SHIFT Ghidra evidence export -> " + outputDir);
        exportBinary();
        exportFunctionsAndCallgraph();
        exportStrings();
        discoverVtables();
        exportVtables();
        exportConstructors();
        exportGlobals();
        exportStaticData();
        exportSwitches();
        exportFactories();
        exportManifest();
        println("SHIFT Ghidra evidence export complete");
    }

    private PrintWriter writer(String name) throws Exception {
        return new PrintWriter(new BufferedWriter(new OutputStreamWriter(
            new FileOutputStream(new File(outputDir, name)), StandardCharsets.UTF_8)));
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

    private static String addressArray(Iterable<Address> values) {
        List<String> rows = new ArrayList<>();
        for (Address value : values) rows.add(addr(value));
        return stringArray(rows);
    }

    private void inc(String key) {
        counts.put(key, counts.getOrDefault(key, 0) + 1);
    }

    private void exportBinary() throws Exception {
        try (PrintWriter out = writer("binary.json")) {
            StringBuilder blocks = new StringBuilder("[");
            boolean first = true;
            for (MemoryBlock block : memory.getBlocks()) {
                if (!first) blocks.append(',');
                first = false;
                blocks.append('{')
                    .append("\"name\":").append(q(block.getName())).append(',')
                    .append("\"start\":").append(q(addr(block.getStart()))).append(',')
                    .append("\"end\":").append(q(addr(block.getEnd()))).append(',')
                    .append("\"size\":").append(block.getSize()).append(',')
                    .append("\"initialized\":").append(block.isInitialized()).append(',')
                    .append("\"read\":").append(block.isRead()).append(',')
                    .append("\"write\":").append(block.isWrite()).append(',')
                    .append("\"execute\":").append(block.isExecute())
                    .append('}');
            }
            blocks.append(']');
            out.println("{" +
                "\"format\":" + q(FORMAT) + "," +
                "\"program_name\":" + q(currentProgram.getName()) + "," +
                "\"executable_path\":" + q(currentProgram.getExecutablePath()) + "," +
                "\"executable_format\":" + q(currentProgram.getExecutableFormat()) + "," +
                "\"executable_md5\":" + q(currentProgram.getExecutableMD5()) + "," +
                "\"language_id\":" + q(currentProgram.getLanguageID().toString()) + "," +
                "\"compiler_spec\":" + q(currentProgram.getCompilerSpec().getCompilerSpecID().toString()) + "," +
                "\"image_base\":" + q(addr(currentProgram.getImageBase())) + "," +
                "\"pointer_size\":" + currentProgram.getDefaultPointerSize() + "," +
                "\"memory_blocks\":" + blocks +
                "}");
        }
    }

    private void exportFunctionsAndCallgraph() throws Exception {
        try (PrintWriter functionOut = writer("functions.jsonl");
             PrintWriter edgeOut = writer("callgraph.jsonl")) {
            FunctionIterator it = functions.getFunctions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Function f = it.next();
                inc("functions");
                LinkedHashSet<String> outgoing = new LinkedHashSet<>();
                StringBuilder params = new StringBuilder("[");
                boolean firstParam = true;
                for (ghidra.program.model.listing.Parameter p : f.getParameters()) {
                    if (!firstParam) params.append(',');
                    firstParam = false;
                    params.append('{')
                        .append("\"name\":").append(q(p.getName())).append(',')
                        .append("\"type\":").append(q(p.getDataType().getDisplayName())).append(',')
                        .append("\"storage\":").append(q(p.getVariableStorage().toString()))
                        .append('}');
                }
                params.append(']');

                String fingerprint = fingerprint(f);
                functionOut.println("{" +
                    "\"address\":" + q(addr(f.getEntryPoint())) + "," +
                    "\"name\":" + q(f.getName()) + "," +
                    "\"namespace\":" + q(f.getParentNamespace().getName(true)) + "," +
                    "\"size\":" + f.getBody().getNumAddresses() + "," +
                    "\"thunk\":" + f.isThunk() + "," +
                    "\"external\":" + f.isExternal() + "," +
                    "\"calling_convention\":" + q(f.getCallingConventionName()) + "," +
                    "\"signature\":" + q(f.getSignature().getPrototypeString()) + "," +
                    "\"parameters\":" + params + "," +
                    "\"mnemonic_sha256\":" + q(fingerprint) +
                    "}");

                InstructionIterator insIt = listing.getInstructions(f.getBody(), true);
                while (insIt.hasNext()) {
                    Instruction ins = insIt.next();
                    boolean emittedCall = false;
                    for (Reference ref : ins.getReferencesFrom()) {
                        if (!ref.getReferenceType().isCall()) continue;
                        emittedCall = true;
                        Address target = ref.getToAddress();
                        Function callee = target == null ? null : functions.getFunctionAt(target);
                        String targetAddress = target == null ? null : addr(target);
                        String targetName = callee == null ? null : callee.getName();
                        if (targetAddress != null) outgoing.add(targetAddress);
                        edgeOut.println("{" +
                            "\"from_function\":" + q(addr(f.getEntryPoint())) + "," +
                            "\"from_name\":" + q(f.getName()) + "," +
                            "\"instruction\":" + q(addr(ins.getAddress())) + "," +
                            "\"to\":" + q(targetAddress) + "," +
                            "\"to_name\":" + q(targetName) + "," +
                            "\"indirect\":false" +
                            "}");
                        inc("call_edges");
                    }
                    if (!emittedCall && ins.getFlowType().isCall() && ins.getFlowType().isComputed()) {
                        edgeOut.println("{" +
                            "\"from_function\":" + q(addr(f.getEntryPoint())) + "," +
                            "\"from_name\":" + q(f.getName()) + "," +
                            "\"instruction\":" + q(addr(ins.getAddress())) + "," +
                            "\"to\":null,\"to_name\":null,\"indirect\":true" +
                            "}");
                        inc("call_edges");
                    }
                }
                callsByFunction.put(addr(f.getEntryPoint()), outgoing);
            }
        }
    }

    private String fingerprint(Function f) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        InstructionIterator it = listing.getInstructions(f.getBody(), true);
        while (it.hasNext()) {
            String mnemonic = it.next().getMnemonicString().toUpperCase();
            digest.update(mnemonic.getBytes(StandardCharsets.US_ASCII));
            digest.update((byte)'\n');
        }
        StringBuilder out = new StringBuilder();
        for (byte b : digest.digest()) out.append(String.format("%02x", b & 0xff));
        return out.toString();
    }

    private void exportStrings() throws Exception {
        try (PrintWriter out = writer("strings_xrefs.jsonl")) {
            Iterator<Data> it = DefinedDataIterator.definedStrings(currentProgram);
            while (it.hasNext() && !monitor.isCancelled()) {
                Data data = it.next();
                String value = data.getValue() == null ? data.getDefaultValueRepresentation() : data.getValue().toString();
                LinkedHashSet<String> xrefs = new LinkedHashSet<>();
                LinkedHashSet<String> functionRefs = new LinkedHashSet<>();
                ReferenceIterator refs = references.getReferencesTo(data.getAddress());
                while (refs.hasNext()) {
                    Reference ref = refs.next();
                    xrefs.add(addr(ref.getFromAddress()));
                    Function f = functions.getFunctionContaining(ref.getFromAddress());
                    if (f != null) {
                        String fa = addr(f.getEntryPoint());
                        functionRefs.add(fa);
                        stringsByFunction.computeIfAbsent(fa, k -> new LinkedHashSet<>()).add(value);
                    }
                }
                out.println("{" +
                    "\"address\":" + q(addr(data.getAddress())) + "," +
                    "\"value\":" + q(value) + "," +
                    "\"length\":" + data.getLength() + "," +
                    "\"xrefs\":" + stringArray(xrefs) + "," +
                    "\"functions\":" + stringArray(functionRefs) +
                    "}");
                inc("strings");
            }
        }
    }

    private Address readPointer(Address address) {
        try {
            int size = currentProgram.getDefaultPointerSize();
            long raw;
            if (size == 4) raw = Integer.toUnsignedLong(memory.getInt(address));
            else if (size == 8) raw = memory.getLong(address);
            else return null;
            return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(raw);
        } catch (Exception ex) {
            return null;
        }
    }

    private void discoverVtables() {
        int pointerSize = currentProgram.getDefaultPointerSize();
        for (MemoryBlock block : memory.getBlocks()) {
            if (monitor.isCancelled()) return;
            if (!block.isInitialized() || block.isExecute()) continue;
            long offset = 0;
            while (offset + (long)MIN_VTABLE_FUNCTIONS * pointerSize <= block.getSize()) {
                Address start;
                try { start = block.getStart().add(offset); }
                catch (Exception ex) { break; }
                List<Address> targets = new ArrayList<>();
                long cursor = offset;
                while (cursor + pointerSize <= block.getSize()) {
                    Address cell;
                    try { cell = block.getStart().add(cursor); }
                    catch (Exception ex) { break; }
                    Address target = readPointer(cell);
                    if (target == null || functions.getFunctionAt(target) == null) break;
                    targets.add(target);
                    cursor += pointerSize;
                    if (targets.size() >= 512) break;
                }
                if (targets.size() >= MIN_VTABLE_FUNCTIONS) {
                    VtableCandidate candidate = new VtableCandidate();
                    candidate.address = start;
                    candidate.block = block.getName();
                    candidate.targets.addAll(targets);
                    LinkedHashSet<String> users = new LinkedHashSet<>();
                    ReferenceIterator refs = references.getReferencesTo(start);
                    while (refs.hasNext()) {
                        Reference ref = refs.next();
                        Function f = functions.getFunctionContaining(ref.getFromAddress());
                        if (f == null) continue;
                        String functionAddress = addr(f.getEntryPoint());
                        users.add(functionAddress);
                        vtablesByFunction.computeIfAbsent(functionAddress, k -> new LinkedHashSet<>()).add(addr(start));
                    }
                    candidate.users.addAll(users);
                    vtables.add(candidate);
                    inc("vtable_candidates");
                    offset = cursor;
                } else {
                    offset += pointerSize;
                }
            }
        }
    }

    private void exportVtables() throws Exception {
        try (PrintWriter out = writer("vtables.json")) {
            out.print("{\"format\":\"SHIFT.GhidraVtableCandidates/1\",\"status\":\"heuristic-candidates\",\"vtables\":[");
            boolean first = true;
            for (VtableCandidate v : vtables) {
                if (!first) out.print(',');
                first = false;
                StringBuilder slots = new StringBuilder("[");
                for (int i = 0; i < v.targets.size(); i++) {
                    if (i > 0) slots.append(',');
                    Function f = functions.getFunctionAt(v.targets.get(i));
                    slots.append('{')
                        .append("\"slot\":").append(i).append(',')
                        .append("\"target\":").append(q(addr(v.targets.get(i)))).append(',')
                        .append("\"name\":").append(q(f == null ? null : f.getName()))
                        .append('}');
                }
                slots.append(']');
                out.print("{" +
                    "\"address\":" + q(addr(v.address)) + "," +
                    "\"block\":" + q(v.block) + "," +
                    "\"slot_count\":" + v.targets.size() + "," +
                    "\"slots\":" + slots + "," +
                    "\"function_xrefs\":" + stringArray(v.users) +
                    "}");
            }
            out.println("]}");
        }
    }

    private void exportConstructors() throws Exception {
        try (PrintWriter out = writer("constructors.jsonl")) {
            List<String> functionAddresses = new ArrayList<>(vtablesByFunction.keySet());
            Collections.sort(functionAddresses);
            for (String fa : functionAddresses) {
                Address address = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(fa.substring(2));
                Function f = functions.getFunctionAt(address);
                if (f == null) continue;
                List<String> preview = instructionPreview(f, MAX_INSTRUCTION_PREVIEW);
                out.println("{" +
                    "\"status\":\"vtable-xref-candidate\"," +
                    "\"function\":" + q(fa) + "," +
                    "\"name\":" + q(f.getName()) + "," +
                    "\"vtables\":" + stringArray(vtablesByFunction.get(fa)) + "," +
                    "\"instruction_preview\":" + stringArray(preview) +
                    "}");
                inc("constructor_candidates");
            }
        }
    }

    private List<String> instructionPreview(Function f, int limit) {
        List<String> result = new ArrayList<>();
        InstructionIterator it = listing.getInstructions(f.getBody(), true);
        while (it.hasNext() && result.size() < limit) {
            Instruction ins = it.next();
            result.add(addr(ins.getAddress()) + " " + ins.toString());
        }
        return result;
    }

    private void exportGlobals() throws Exception {
        try (PrintWriter out = writer("globals.jsonl")) {
            SymbolIterator it = currentProgram.getSymbolTable().getAllSymbols(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Symbol symbol = it.next();
                if (symbol.getSymbolType() != SymbolType.LABEL) continue;
                Address a = symbol.getAddress();
                if (a == null || !memory.contains(a)) continue;
                if (functions.getFunctionAt(a) != null) continue;
                Data data = listing.getDataAt(a);
                int refCount = 0;
                ReferenceIterator refs = references.getReferencesTo(a);
                while (refs.hasNext()) { refs.next(); refCount++; }
                out.println("{" +
                    "\"address\":" + q(addr(a)) + "," +
                    "\"name\":" + q(symbol.getName(true)) + "," +
                    "\"data_type\":" + q(data == null ? null : data.getDataType().getDisplayName()) + "," +
                    "\"length\":" + (data == null ? 0 : data.getLength()) + "," +
                    "\"reference_count\":" + refCount +
                    "}");
                inc("globals");
            }
        }
    }

    private void exportStaticData() throws Exception {
        try (PrintWriter out = writer("static_tables.jsonl")) {
            DataIterator it = listing.getDefinedData(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Data data = it.next();
                MemoryBlock block = memory.getBlock(data.getAddress());
                if (block == null || !block.isInitialized() || block.isExecute()) continue;
                DataType dt = data.getDataType();
                int length = data.getLength();
                boolean tableLike = dt instanceof Array || dt instanceof Pointer || data.getNumComponents() > 1 || length >= 8;
                if (!tableLike) continue;
                String bytes = readBytesHex(data.getAddress(), Math.min(length, MAX_RAW_DATA_BYTES));
                out.println("{" +
                    "\"address\":" + q(addr(data.getAddress())) + "," +
                    "\"block\":" + q(block.getName()) + "," +
                    "\"data_type\":" + q(dt.getDisplayName()) + "," +
                    "\"length\":" + length + "," +
                    "\"components\":" + data.getNumComponents() + "," +
                    "\"raw_hex\":" + q(bytes) + "," +
                    "\"raw_truncated\":" + (length > MAX_RAW_DATA_BYTES) +
                    "}");
                inc("static_data");
            }
        }
    }

    private String readBytesHex(Address address, int length) {
        if (length <= 0) return "";
        byte[] bytes = new byte[length];
        try {
            int got = memory.getBytes(address, bytes);
            StringBuilder out = new StringBuilder(got * 2);
            for (int i = 0; i < got; i++) out.append(String.format("%02x", bytes[i] & 0xff));
            return out.toString();
        } catch (MemoryAccessException ex) {
            return null;
        }
    }

    private void exportSwitches() throws Exception {
        try (PrintWriter out = writer("switches.jsonl")) {
            FunctionIterator fit = functions.getFunctions(true);
            while (fit.hasNext() && !monitor.isCancelled()) {
                Function f = fit.next();
                InstructionIterator it = listing.getInstructions(f.getBody(), true);
                while (it.hasNext()) {
                    Instruction ins = it.next();
                    if (!ins.getFlowType().isJump() || !ins.getFlowType().isComputed()) continue;
                    Address[] flows = ins.getFlows();
                    List<Address> destinations = new ArrayList<>();
                    if (flows != null) Collections.addAll(destinations, flows);
                    out.println("{" +
                        "\"status\":\"computed-jump-candidate\"," +
                        "\"function\":" + q(addr(f.getEntryPoint())) + "," +
                        "\"name\":" + q(f.getName()) + "," +
                        "\"instruction\":" + q(addr(ins.getAddress())) + "," +
                        "\"text\":" + q(ins.toString()) + "," +
                        "\"destinations\":" + addressArray(destinations) +
                        "}");
                    inc("switch_candidates");
                }
            }
        }
    }

    private void exportFactories() throws Exception {
        try (PrintWriter out = writer("factories.jsonl")) {
            List<String> addresses = new ArrayList<>(stringsByFunction.keySet());
            Collections.sort(addresses);
            for (String fa : addresses) {
                LinkedHashSet<String> strings = stringsByFunction.get(fa);
                LinkedHashSet<String> calls = callsByFunction.getOrDefault(fa, new LinkedHashSet<>());
                if (strings == null || strings.isEmpty() || calls.isEmpty()) continue;
                Address address = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(fa.substring(2));
                Function f = functions.getFunctionAt(address);
                if (f == null) continue;
                out.println("{" +
                    "\"status\":\"string-plus-call-candidate\"," +
                    "\"function\":" + q(fa) + "," +
                    "\"name\":" + q(f.getName()) + "," +
                    "\"strings\":" + stringArray(strings) + "," +
                    "\"direct_calls\":" + stringArray(calls) +
                    "}");
                inc("factory_candidates");
            }
        }
    }

    private void exportManifest() throws Exception {
        try (PrintWriter out = writer("manifest.json")) {
            StringBuilder countJson = new StringBuilder("{");
            boolean first = true;
            for (Map.Entry<String, Integer> entry : counts.entrySet()) {
                if (!first) countJson.append(',');
                first = false;
                countJson.append(q(entry.getKey())).append(':').append(entry.getValue());
            }
            countJson.append('}');
            out.println("{" +
                "\"format\":" + q(FORMAT) + "," +
                "\"program\":" + q(currentProgram.getName()) + "," +
                "\"counts\":" + countJson + "," +
                "\"files\":[" +
                    q("binary.json") + "," + q("functions.jsonl") + "," + q("callgraph.jsonl") + "," +
                    q("vtables.json") + "," + q("constructors.jsonl") + "," + q("strings_xrefs.jsonl") + "," +
                    q("globals.jsonl") + "," + q("static_tables.jsonl") + "," + q("switches.jsonl") + "," +
                    q("factories.jsonl") + "]" +
                "}");
        }
    }
}
