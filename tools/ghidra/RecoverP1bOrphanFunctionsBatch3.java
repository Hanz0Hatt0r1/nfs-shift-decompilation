import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.symbol.SourceType;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Restore three verified caller bodies from the isolated SHIFT project copy. */
public class RecoverP1bOrphanFunctionsBatch3 extends GhidraScript {
    private static final String RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b";
    private static final String PLAN_HEADER =
        "entry\tend\tprevious_address\tprevious_mnemonic\tprevious_bytes\tprevious_target"
        + "\tboundary_gap_hex\tentry_evidence\texternal_flows\tcallsites"
        + "\tinstruction_count\tpcode_instruction_count\tcall_instruction_count"
        + "\tbranch_instruction_count\tbody_bytes\tbody_sha256";

    private Listing listing;
    private FunctionManager functions;
    private ReferenceManager references;
    private Memory memory;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException(
                "Usage: RecoverP1bOrphanFunctionsBatch3.java <plan.tsv> <output.tsv>");
        }
        if (!RETAIL_MD5.equalsIgnoreCase(currentProgram.getExecutableMD5())) {
            throw new IllegalStateException("program is not the pinned SHIFT retail executable");
        }

        List<Candidate> candidates = loadCandidates(new File(args[0]));
        listing = currentProgram.getListing();
        functions = currentProgram.getFunctionManager();
        references = currentProgram.getReferenceManager();
        memory = currentProgram.getMemory();
        List<String> results = new ArrayList<>();
        Set<String> seenEntries = new HashSet<>();
        Set<String> seenCallsites = new HashSet<>();
        int transaction = currentProgram.startTransaction("Recover verified P1B orphan callers batch 3");
        boolean commit = false;
        try {
            for (Candidate candidate : candidates) {
                monitor.checkCancelled();
                Address entry = parse(candidate.entry);
                Address end = parse(candidate.end);
                if (!seenEntries.add(entry.toString())) {
                    throw new IllegalStateException("duplicate function entry: " + candidate.entry);
                }
                if (functions.getFunctionAt(entry) != null || functions.getFunctionContaining(entry) != null) {
                    throw new IllegalStateException("entry already belongs to a function: " + candidate.entry);
                }
                MemoryBlock entryBlock = memory.getBlock(entry);
                if (entryBlock == null || !entryBlock.isExecute() || !".text".equals(entryBlock.getName())) {
                    throw new IllegalStateException("entry is outside executable .text: " + candidate.entry);
                }

                verifyEntryEvidence(candidate, entry);
                verifyPrecedingBoundary(candidate, entry);
                Instruction last = listing.getInstructionAt(end);
                if (last == null) throw new IllegalStateException("missing terminal instruction: " + candidate.end);
                AddressSet body = new AddressSet(entry, last.getMaxAddress());
                BodyFacts facts = verifyBody(candidate, body, last);
                verifyCallsites(candidate, body, seenCallsites);

                String entryText = entry.toString(false, false).toLowerCase();
                Function function = functions.createFunction(
                    "FUN_" + entryText, entry, body, SourceType.USER_DEFINED);
                if (function == null
                    || !function.getEntryPoint().equals(entry)
                    || function.getBody().getNumAddresses() != candidate.bodyBytes) {
                    throw new IllegalStateException("Ghidra did not create the exact function body: " + candidate.entry);
                }
                verifyExternalOwners(candidate, body);
                for (Callsite callsite : candidate.callsites) {
                    Function owner = functions.getFunctionContaining(parse(callsite.address));
                    if (owner == null || !owner.getEntryPoint().equals(entry)) {
                        throw new IllegalStateException("recovered function does not own exact callsite: " + callsite.address);
                    }
                }
                results.add(candidate.toResultRow(function.getName(), facts));
            }
            commit = true;
        } finally {
            currentProgram.endTransaction(transaction, commit);
        }

        File output = new File(args[1]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create output directory");
        }
        try (BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(output), StandardCharsets.UTF_8))) {
            writer.write("entry\tfunction_name\tend\tbody_bytes\tinstruction_count\tpcode_instruction_count"
                + "\tcall_instruction_count\tbranch_instruction_count\tbody_sha256"
                + "\towned_callsites\texternal_flows");
            writer.newLine();
            for (String row : results) {
                writer.write(row);
                writer.newLine();
            }
        }
        println("Recovered " + results.size() + " verified orphan caller bodies -> " + output);
    }

    private List<Candidate> loadCandidates(File plan) throws Exception {
        List<Candidate> result = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                new FileInputStream(plan), StandardCharsets.UTF_8))) {
            if (!PLAN_HEADER.equals(reader.readLine())) throw new IllegalArgumentException("unexpected batch 3 plan header");
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) continue;
                String[] fields = line.split("\t", -1);
                if (fields.length != 16) throw new IllegalArgumentException("unexpected batch 3 plan row width");
                result.add(new Candidate(fields));
            }
        }
        if (result.isEmpty()) throw new IllegalArgumentException("empty batch 3 recovery plan");
        return result;
    }

    private void verifyEntryEvidence(Candidate candidate, Address entry) throws Exception {
        Set<String> found = new HashSet<>();
        for (EntryEvidence evidence : candidate.entryEvidence) {
            Address source = parse(evidence.source);
            if ("RAW_U32".equals(evidence.kind)) {
                MemoryBlock block = memory.getBlock(source);
                long value = Integer.toUnsignedLong(memory.getInt(source));
                if (block == null || !".rdata".equals(block.getName()) || value != entry.getOffset()) {
                    throw new IllegalStateException("raw .rdata entry pointer drift at " + evidence.source);
                }
                found.add(evidence.key());
                continue;
            }
            ReferenceIterator iterator = references.getReferencesTo(entry);
            boolean matched = false;
            while (iterator.hasNext()) {
                Reference reference = iterator.next();
                if (!reference.getFromAddress().equals(source)) continue;
                String type = reference.getReferenceType().toString();
                if ("DATA".equals(evidence.kind) && reference.getReferenceType().isData()) matched = true;
                if ("JUMP".equals(evidence.kind) && reference.getReferenceType().isJump()
                    && "UNCONDITIONAL_JUMP".equals(type)) matched = true;
            }
            if (!matched) throw new IllegalStateException("missing exact entry reference: " + evidence.source + " -> " + candidate.entry);
            found.add(evidence.key());
        }
        if (found.size() != candidate.entryEvidence.size()) {
            throw new IllegalStateException("entry evidence count drift at " + candidate.entry);
        }
    }

    private void verifyPrecedingBoundary(Candidate candidate, Address entry) throws Exception {
        Address previousAddress = parse(candidate.previousAddress);
        Instruction previous = listing.getInstructionAt(previousAddress);
        if (previous == null || !previous.getAddress().equals(previousAddress)) {
            throw new IllegalStateException("preceding instruction drift at " + candidate.entry);
        }
        if (!previous.getMnemonicString().toUpperCase().startsWith(candidate.previousMnemonic)
            || !toHex(previous.getBytes()).equals(candidate.previousBytes)) {
            throw new IllegalStateException("preceding instruction bytes drift at " + candidate.entry);
        }
        if (!previous.getMnemonicString().toUpperCase().startsWith("RET")
            && !previous.getMnemonicString().toUpperCase().startsWith("JMP")) {
            throw new IllegalStateException("preceding boundary is not terminal at " + candidate.entry);
        }
        Address gapStart = previous.getMaxAddress().add(1);
        int gapSize = (int) entry.subtract(gapStart);
        if (gapSize < 0) throw new IllegalStateException("preceding instruction overlaps entry: " + candidate.entry);
        byte[] gap = new byte[gapSize];
        if (gapSize > 0) memory.getBytes(gapStart, gap);
        if (!toHex(gap).equals(candidate.boundaryGapHex)) {
            throw new IllegalStateException("boundary padding drift at " + candidate.entry);
        }
        for (int i = 0; i < gapSize; i++) {
            if ((gap[i] & 0xff) != 0xcc) throw new IllegalStateException("non-padding byte before entry: " + candidate.entry);
            if (functions.getFunctionContaining(gapStart.add(i)) != null) {
                throw new IllegalStateException("boundary padding has a function owner: " + candidate.entry);
            }
        }
        if (!"-".equals(candidate.previousTarget)) {
            Address[] flows = previous.getFlows();
            if (flows.length != 1 || !flows[0].equals(parse(candidate.previousTarget))) {
                throw new IllegalStateException("preceding transfer target drift at " + candidate.entry);
            }
        }
    }

    private BodyFacts verifyBody(Candidate candidate, AddressSet body, Instruction last) throws Exception {
        Address entry = parse(candidate.entry);
        Address endExclusive = last.getMaxAddress().add(1);
        if (!endExclusive.equals(parse(candidate.end).add(last.getLength()))) {
            throw new IllegalStateException("terminal instruction boundary drift at " + candidate.entry);
        }
        Address expected = entry;
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        List<Instruction> instructions = new ArrayList<>();
        int pcode = 0;
        int calls = 0;
        int branches = 0;
        InstructionIterator iterator = listing.getInstructions(body, true);
        while (iterator.hasNext()) {
            monitor.checkCancelled();
            Instruction instruction = iterator.next();
            if (!instruction.getAddress().equals(expected)) {
                throw new IllegalStateException("instruction gap in body at " + candidate.entry);
            }
            if (functions.getFunctionAt(instruction.getAddress()) != null
                || functions.getFunctionContaining(instruction.getAddress()) != null) {
                throw new IllegalStateException("body instruction already has an owner: " + instruction.getAddress());
            }
            MemoryBlock block = memory.getBlock(instruction.getAddress());
            if (block == null || !block.isExecute() || !".text".equals(block.getName())) {
                throw new IllegalStateException("body instruction is outside executable .text: " + instruction.getAddress());
            }
            byte[] bytes = instruction.getBytes();
            digest.update(bytes);
            expected = instruction.getMaxAddress().add(1);
            if (instruction.getPcode().length == 0) throw new IllegalStateException("missing P-code at " + instruction.getAddress());
            pcode++;
            String flowName = instruction.getFlowType().toString().toUpperCase();
            if (flowName.contains("CALL")) calls++;
            if (flowName.contains("JUMP")) branches++;
            instructions.add(instruction);
            if (instruction.getFlowType().isJump()) {
                Address[] flows = instruction.getFlows();
                if (flows.length == 0) throw new IllegalStateException("jump has no recorded target at " + instruction.getAddress());
                for (Address target : flows) {
                    if (!body.contains(target) && !candidate.allowsExternal(instruction.getAddress(), target)) {
                        throw new IllegalStateException("unrecorded external branch at " + instruction.getAddress() + " -> " + target);
                    }
                }
            }
        }
        int bytes = (int) body.getNumAddresses();
        String hash = toHex(digest.digest());
        if (!expected.equals(endExclusive)
            || instructions.isEmpty()
            || instructions.get(instructions.size() - 1) != last
            || instructions.size() != candidate.instructionCount
            || pcode != candidate.pcodeInstructionCount
            || calls != candidate.callInstructionCount
            || branches != candidate.branchInstructionCount
            || bytes != candidate.bodyBytes
            || !candidate.bodySha256.equals(hash)) {
            throw new IllegalStateException("verified body facts drift at " + candidate.entry);
        }
        verifyReachability(candidate, body, instructions);
        return new BodyFacts(instructions.size(), pcode, calls, branches, bytes, hash);
    }

    private void verifyReachability(Candidate candidate, AddressSet body, List<Instruction> instructions) {
        java.util.Map<String, Instruction> byAddress = new java.util.HashMap<>();
        for (Instruction instruction : instructions) byAddress.put(instruction.getAddress().toString(), instruction);
        Set<String> reached = new HashSet<>();
        ArrayDeque<Address> pending = new ArrayDeque<>();
        pending.add(parse(candidate.entry));
        while (!pending.isEmpty()) {
            Address address = pending.removeFirst();
            String key = address.toString();
            if (!reached.add(key)) continue;
            Instruction instruction = byAddress.get(key);
            if (instruction == null) {
                if (candidate.allowsExternalEntry(address)) continue;
                throw new IllegalStateException("CFG leaves the body without recorded external edge at " + address);
            }
            String flow = instruction.getFlowType().toString();
            if (instruction.getFlowType().isJump()) {
                for (Address target : instruction.getFlows()) {
                    if (body.contains(target)) pending.add(target);
                    else if (!candidate.allowsExternal(instruction.getAddress(), target)) {
                        throw new IllegalStateException("CFG edge leaves the body at " + instruction.getAddress() + " -> " + target);
                    }
                }
                if (instruction.getFlowType().isConditional() && instruction.getFallThrough() != null) {
                    pending.add(instruction.getFallThrough());
                }
            } else if (!flow.contains("TERMINATOR") && instruction.getFallThrough() != null) {
                pending.add(instruction.getFallThrough());
            }
        }
        if (reached.size() != instructions.size()) {
            throw new IllegalStateException("body has unreachable instructions at " + candidate.entry);
        }
    }

    private void verifyCallsites(Candidate candidate, AddressSet body, Set<String> seen) {
        if (candidate.callsites.isEmpty()) throw new IllegalStateException("no planned orphan callsites: " + candidate.entry);
        for (Callsite callsite : candidate.callsites) {
            if (!seen.add(callsite.address.toLowerCase())) throw new IllegalStateException("duplicate planned callsite: " + callsite.address);
            Address address = parse(callsite.address);
            Address target = parse(callsite.target);
            Instruction instruction = listing.getInstructionAt(address);
            if (!body.contains(address) || instruction == null || !instruction.getFlowType().isCall()) {
                throw new IllegalStateException("expected exact call instruction at " + callsite.address);
            }
            boolean found = false;
            for (Reference reference : instruction.getReferencesFrom()) {
                if (reference.getReferenceType().isCall() && reference.getToAddress().equals(target)) found = true;
            }
            if (!found) throw new IllegalStateException("missing exact call target at " + callsite.address);
        }
    }

    private void verifyExternalOwners(Candidate candidate, AddressSet body) {
        for (ExternalFlow flow : candidate.externalFlows) {
            Address source = parse(flow.source);
            Address target = parse(flow.target);
            Instruction instruction = listing.getInstructionAt(source);
            if (!body.contains(source)) throw new IllegalStateException("external edge source is outside the body: " + flow.source);
            if (instruction == null || (!instruction.getFlowType().isJump()
                && !"CALL_TERMINATOR".equals(instruction.getFlowType().toString()))) {
                throw new IllegalStateException("external edge source is not a jump: " + flow.source);
            }
            if ("TAIL".equals(flow.kind) && !"CALL_TERMINATOR".equals(instruction.getFlowType().toString())) {
                throw new IllegalStateException("tail edge is not a Ghidra CALL_TERMINATOR: " + flow.source);
            }
            if ("SHARED_BRANCH".equals(flow.kind) && !instruction.getFlowType().isConditional()) {
                throw new IllegalStateException("shared edge is not a conditional branch: " + flow.source);
            }
            boolean found = false;
            for (Address destination : instruction.getFlows()) if (destination.equals(target)) found = true;
            if (!found) throw new IllegalStateException("external edge target drift: " + flow.source + " -> " + flow.target);
            Function owner = functions.getFunctionContaining(target);
            if (owner == null || !owner.getEntryPoint().equals(parse(flow.expectedOwner))) {
                throw new IllegalStateException("shared-edge target owner drift: " + flow.target);
            }
        }
    }

    private Address parse(String token) {
        String value = token.trim();
        if (value.startsWith("0x") || value.startsWith("0X")) value = value.substring(2);
        return toAddr(Long.parseUnsignedLong(value, 16));
    }

    private static String toHex(byte[] bytes) {
        StringBuilder result = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) result.append(String.format("%02x", value & 0xff));
        return result.toString();
    }

    private final class Candidate {
        private final String entry, end, previousAddress, previousMnemonic, previousBytes, previousTarget;
        private final String boundaryGapHex, bodySha256;
        private final List<EntryEvidence> entryEvidence = new ArrayList<>();
        private final List<ExternalFlow> externalFlows = new ArrayList<>();
        private final List<Callsite> callsites = new ArrayList<>();
        private final int instructionCount, pcodeInstructionCount, callInstructionCount, branchInstructionCount, bodyBytes;

        Candidate(String[] fields) {
            entry = fields[0]; end = fields[1]; previousAddress = fields[2]; previousMnemonic = fields[3];
            previousBytes = fields[4].toLowerCase(); previousTarget = fields[5]; boundaryGapHex = fields[6].toLowerCase();
            for (String value : splitList(fields[7])) entryEvidence.add(new EntryEvidence(value));
            for (String value : splitList(fields[8])) externalFlows.add(new ExternalFlow(value));
            for (String value : splitList(fields[9])) callsites.add(new Callsite(value));
            instructionCount = Integer.parseInt(fields[10]); pcodeInstructionCount = Integer.parseInt(fields[11]);
            callInstructionCount = Integer.parseInt(fields[12]); branchInstructionCount = Integer.parseInt(fields[13]);
            bodyBytes = Integer.parseInt(fields[14]); bodySha256 = fields[15].toLowerCase();
        }

        boolean allowsExternal(Address source, Address target) {
            for (ExternalFlow flow : externalFlows) {
                if (parse(flow.source).equals(source) && parse(flow.target).equals(target)) return true;
            }
            return false;
        }

        boolean allowsExternalEntry(Address address) {
            for (ExternalFlow flow : externalFlows) if (parse(flow.target).equals(address)) return true;
            return false;
        }

        String toResultRow(String functionName, BodyFacts facts) {
            List<String> calls = new ArrayList<>();
            for (Callsite callsite : callsites) calls.add(callsite.address + ">" + callsite.target);
            List<String> edges = new ArrayList<>();
            for (ExternalFlow flow : externalFlows) edges.add(flow.source + ">" + flow.target + ":" + flow.kind);
            return entry + "\t" + functionName + "\t" + end + "\t" + facts.bytes + "\t" + facts.instructions
                + "\t" + facts.pcode + "\t" + facts.calls + "\t" + facts.branches + "\t" + facts.sha256
                + "\t" + String.join(";", calls) + "\t" + String.join(";", edges);
        }
    }

    private static List<String> splitList(String value) {
        List<String> values = new ArrayList<>();
        if (value == null || value.trim().isEmpty() || "-".equals(value)) return values;
        for (String item : value.split(";")) if (!item.trim().isEmpty()) values.add(item.trim());
        return values;
    }

    private final class EntryEvidence {
        private final String kind, source, target;
        EntryEvidence(String value) {
            String[] fields = value.split(",", -1);
            if (fields.length != 3) throw new IllegalArgumentException("malformed entry evidence: " + value);
            kind = fields[0]; source = fields[1]; target = fields[2];
        }
        String key() { return kind + "," + source + "," + target; }
    }

    private final class ExternalFlow {
        private final String source, target, kind, expectedOwner;
        ExternalFlow(String value) {
            String[] fields = value.split(",", -1);
            if (fields.length != 4) throw new IllegalArgumentException("malformed external flow: " + value);
            source = fields[0]; target = fields[1]; kind = fields[2]; expectedOwner = fields[3];
        }
    }

    private final class Callsite {
        private final String address, target;
        Callsite(String value) {
            String[] fields = value.split(">", -1);
            if (fields.length != 2) throw new IllegalArgumentException("malformed orphan callsite: " + value);
            address = fields[0]; target = fields[1];
        }
    }

    private static final class BodyFacts {
        final int instructions, pcode, calls, branches, bytes;
        final String sha256;
        BodyFacts(int instructions, int pcode, int calls, int branches, int bytes, String sha256) {
            this.instructions = instructions; this.pcode = pcode; this.calls = calls;
            this.branches = branches; this.bytes = bytes; this.sha256 = sha256;
        }
    }
}
