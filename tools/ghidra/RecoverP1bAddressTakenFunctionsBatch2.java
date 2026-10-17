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
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Recover a hash-pinned batch of address-taken orphan caller bodies in an isolated SHIFT copy. */
public class RecoverP1bAddressTakenFunctionsBatch2 extends GhidraScript {
    private static final String RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b";
    private static final String PLAN_HEADER =
        "entry\tend\tterminator\tterminal_target\tprevious_address\tprevious_mnemonic\tprevious_bytes"
        + "\tprevious_target\tboundary_gap_hex\tentry_reference_sources\tcallsites\ttargets"
        + "\tinstruction_count\tpcode_instruction_count\tcall_instruction_count\tbranch_instruction_count"
        + "\tbody_bytes\tbody_sha256";

    private Listing listing;
    private FunctionManager functions;
    private ReferenceManager references;
    private Memory memory;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException(
                "Usage: RecoverP1bAddressTakenFunctionsBatch2.java <plan.tsv> <output.tsv>");
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
        int transaction = currentProgram.startTransaction("Recover verified P1B address-taken callers batch 2");
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

                verifyEntryReferences(candidate, entry);
                verifyPrecedingBoundary(candidate, entry);
                Instruction last = listing.getInstructionAt(end);
                if (last == null || !last.getMnemonicString().toUpperCase().startsWith(candidate.terminalMnemonic)) {
                    throw new IllegalStateException("unexpected terminal instruction at " + candidate.end);
                }
                if (candidate.terminalTarget != null) {
                    Address[] terminalFlows = last.getFlows();
                    if (terminalFlows.length != 1 || !terminalFlows[0].equals(parse(candidate.terminalTarget))) {
                        throw new IllegalStateException("unexpected terminal transfer target at " + candidate.end);
                    }
                }

                AddressSet body = new AddressSet(entry, last.getMaxAddress());
                Address expected = entry;
                int instructionCount = 0;
                int pcodeInstructionCount = 0;
                int callInstructionCount = 0;
                int branchInstructionCount = 0;
                MessageDigest bodyDigest = MessageDigest.getInstance("SHA-256");
                Instruction finalInstruction = null;
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
                    bodyDigest.update(bytes);
                    expected = instruction.getMaxAddress().add(1);
                    if (instruction.getPcode().length == 0) {
                        throw new IllegalStateException("missing P-code at " + instruction.getAddress());
                    }
                    pcodeInstructionCount++;
                    if (instruction.getFlowType().isCall()) callInstructionCount++;
                    if (instruction.getFlowType().isJump()) branchInstructionCount++;
                    if (instruction.getFlowType().isJump()) {
                        Address[] flows = instruction.getFlows();
                        if (flows.length == 0) {
                            throw new IllegalStateException("jump has no recorded destination at " + instruction.getAddress());
                        }
                        for (Address target : flows) {
                            boolean terminalTailJump = instruction == last
                                && candidate.terminalTarget != null
                                && target.equals(parse(candidate.terminalTarget));
                            if (!body.contains(target) && !terminalTailJump) {
                                throw new IllegalStateException("branch leaves bounded body at " + instruction.getAddress()
                                    + " -> " + target);
                            }
                        }
                    }
                    finalInstruction = instruction;
                    instructionCount++;
                }

                String bodyHash = toHex(bodyDigest.digest());
                if (finalInstruction != last
                    || !expected.equals(last.getMaxAddress().add(1))
                    || instructionCount != candidate.instructionCount
                    || pcodeInstructionCount != candidate.pcodeInstructionCount
                    || body.getNumAddresses() != candidate.bodyBytes
                    || callInstructionCount != candidate.callInstructionCount
                    || branchInstructionCount != candidate.branchInstructionCount
                    || !candidate.bodySha256.equals(bodyHash)) {
                    throw new IllegalStateException("bounded body facts drifted at " + candidate.entry);
                }
                verifyCallsites(candidate, seenCallsites);

                String entryText = entry.toString(false, false).toLowerCase();
                Function function = functions.createFunction(
                    "FUN_" + entryText, entry, body, SourceType.USER_DEFINED);
                if (function == null
                    || !function.getEntryPoint().equals(entry)
                    || function.getBody().getNumAddresses() != candidate.bodyBytes) {
                    throw new IllegalStateException("Ghidra did not create the exact function body: " + candidate.entry);
                }
                for (String callsite : candidate.callsites) {
                    Function owner = functions.getFunctionContaining(parse(callsite));
                    if (owner == null || !owner.getEntryPoint().equals(entry)) {
                        throw new IllegalStateException("recovered function does not own exact callsite: " + callsite);
                    }
                }
                results.add(candidate.toResultRow(function.getName()));
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
                + "\tcall_instruction_count\tbranch_instruction_count\tbody_sha256\towned_callsites");
            writer.newLine();
            for (String row : results) {
                writer.write(row);
                writer.newLine();
            }
        }
        println("Recovered " + results.size() + " address-taken orphan functions -> " + output);
    }

    private List<Candidate> loadCandidates(File plan) throws Exception {
        List<Candidate> result = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                new FileInputStream(plan), StandardCharsets.UTF_8))) {
            if (!PLAN_HEADER.equals(reader.readLine())) {
                throw new IllegalArgumentException("unexpected P1B batch 2 plan header");
            }
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) continue;
                String[] cells = line.split("\\t", -1);
                if (cells.length != 18) throw new IllegalArgumentException("invalid plan row: " + line);
                result.add(new Candidate(cells));
            }
        }
        if (result.isEmpty()) throw new IllegalArgumentException("empty P1B batch 2 plan");
        return result;
    }

    private void verifyEntryReferences(Candidate candidate, Address entry) {
        Set<String> expectedSources = new HashSet<>();
        for (String source : candidate.referenceSources) expectedSources.add(parse(source).toString());
        Set<String> foundSources = new HashSet<>();
        for (Reference reference : references.getReferencesTo(entry)) {
            if (reference.getReferenceType().isData() && expectedSources.contains(reference.getFromAddress().toString())) {
                foundSources.add(reference.getFromAddress().toString());
            }
        }
        if (expectedSources.isEmpty() || !foundSources.equals(expectedSources)) {
            throw new IllegalStateException("missing exact address-taken reference at " + candidate.entry);
        }
    }

    private void verifyPrecedingBoundary(Candidate candidate, Address entry) throws Exception {
        Instruction previous = listing.getInstructionBefore(entry);
        if (candidate.previousAddress == null) {
            if (previous != null && previous.getMaxAddress().add(0x20).compareTo(entry) >= 0) {
                throw new IllegalStateException("unexpected instruction immediately before address-taken entry: " + candidate.entry);
            }
            return;
        }
        if (previous == null || !previous.getAddress().equals(parse(candidate.previousAddress))) {
            throw new IllegalStateException("preceding instruction drift at " + candidate.entry);
        }
        if (!previous.getMnemonicString().toUpperCase().startsWith(candidate.previousMnemonic)) {
            throw new IllegalStateException("unexpected preceding boundary at " + candidate.entry);
        }
        if (!toHex(previous.getBytes()).equals(candidate.previousBytes)) {
            throw new IllegalStateException("preceding instruction bytes drift at " + candidate.entry);
        }
        if (!previous.getMnemonicString().toUpperCase().startsWith("RET")
            && !previous.getMnemonicString().toUpperCase().startsWith("JMP")) {
            throw new IllegalStateException("preceding instruction is not a terminal boundary at " + candidate.entry);
        }
        Address gapStart = previous.getMaxAddress().add(1);
        if (gapStart.compareTo(entry) > 0) {
            throw new IllegalStateException("preceding instruction overlaps function entry: " + candidate.entry);
        }
        byte[] gap = new byte[(int) gapStart.subtract(entry) * -1];
        if (gap.length > 0) memory.getBytes(gapStart, gap);
        if (!toHex(gap).equals(candidate.boundaryGapHex)) {
            throw new IllegalStateException("bytes between terminal boundary and entry drift at " + candidate.entry);
        }
        if (candidate.previousTarget != null) {
            Address[] flows = previous.getFlows();
            if (flows.length != 1 || !flows[0].equals(parse(candidate.previousTarget))) {
                throw new IllegalStateException("preceding transfer target drift at " + candidate.entry);
            }
        }
    }

    private void verifyCallsites(Candidate candidate, Set<String> seenCallsites) {
        if (candidate.callsites.length != candidate.targets.length || candidate.callsites.length == 0) {
            throw new IllegalStateException("callsite/target plan mismatch: " + candidate.entry);
        }
        for (int i = 0; i < candidate.callsites.length; i++) {
            String siteText = candidate.callsites[i];
            if (!seenCallsites.add(siteText.toLowerCase())) {
                throw new IllegalStateException("duplicate orphan callsite in plan: " + siteText);
            }
            Address callsite = parse(siteText);
            Address target = parse(candidate.targets[i]);
            Instruction instruction = listing.getInstructionAt(callsite);
            if (instruction == null || !instruction.getFlowType().isCall()) {
                throw new IllegalStateException("expected direct call instruction at " + siteText);
            }
            boolean exactCall = false;
            for (Reference reference : instruction.getReferencesFrom()) {
                if (reference.getReferenceType().isCall() && reference.getToAddress().equals(target)) exactCall = true;
            }
            if (!exactCall) throw new IllegalStateException("missing exact call reference at " + siteText);
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
        private final String entry;
        private final String end;
        private final String terminalMnemonic;
        private final String terminalTarget;
        private final String previousAddress;
        private final String previousMnemonic;
        private final String previousBytes;
        private final String previousTarget;
        private final String boundaryGapHex;
        private final String[] referenceSources;
        private final String[] callsites;
        private final String[] targets;
        private final int instructionCount;
        private final int pcodeInstructionCount;
        private final int callInstructionCount;
        private final int branchInstructionCount;
        private final int bodyBytes;
        private final String bodySha256;

        private Candidate(String[] cells) {
            entry = cells[0];
            end = cells[1];
            terminalMnemonic = cells[2].toUpperCase();
            terminalTarget = optional(cells[3]);
            previousAddress = optional(cells[4]);
            previousMnemonic = optional(cells[5]);
            previousBytes = optional(cells[6]);
            previousTarget = optional(cells[7]);
            boundaryGapHex = cells[8].equals("-") ? "" : cells[8].toLowerCase();
            referenceSources = splitList(cells[9]);
            callsites = splitList(cells[10]);
            targets = splitList(cells[11]);
            instructionCount = Integer.parseInt(cells[12]);
            pcodeInstructionCount = Integer.parseInt(cells[13]);
            callInstructionCount = Integer.parseInt(cells[14]);
            branchInstructionCount = Integer.parseInt(cells[15]);
            bodyBytes = Integer.parseInt(cells[16]);
            bodySha256 = cells[17].toLowerCase();
        }

        private String toResultRow(String functionName) {
            return entry + "\t" + functionName + "\t" + end + "\t" + bodyBytes + "\t"
                + instructionCount + "\t" + pcodeInstructionCount + "\t" + callInstructionCount + "\t"
                + branchInstructionCount + "\t" + bodySha256 + "\t" + String.join(";", callsites);
        }
    }

    private static String optional(String value) {
        return value == null || value.equals("-") || value.isEmpty() ? null : value;
    }

    private static String[] splitList(String value) {
        if (value == null || value.equals("-") || value.isEmpty()) return new String[0];
        return value.split(";");
    }
}
