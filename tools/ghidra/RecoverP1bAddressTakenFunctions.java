import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.symbol.SourceType;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Recover caller-reviewed, address-taken orphan bodies in an isolated SHIFT project copy. */
public class RecoverP1bAddressTakenFunctions extends GhidraScript {
    private static final String RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b";
    private static final Candidate[] CANDIDATES = {
        new Candidate(
            "0x00910aa5", "0x00911394", "RET", null, null,
            new String[] {"0x009080a0", "0x0090296c"},
            new String[] {"0x00910d62", "0x009112e7"},
            new String[] {"0x009113b5", "0x009113b5"},
            703, 2288, 26,
            "8d0dcdc80a86283c6d8c10881894eced65b326b1897c4e93f123919daaba02b6"),
        new Candidate(
            "0x00a9a86e", "0x00a9a873", "JMP", "0x0092e065", null,
            new String[] {"0x00aa98dc"},
            new String[] {}, new String[] {},
            2, 10, 0,
            "ab67469d1bf994dc09f572e70f516762513da2b4aedbf001005f01748bf7c88f"),
        new Candidate(
            "0x00a9a878", "0x00a9a88d", "RET", null, "0x0092e065",
            new String[] {"0x00aa98e0"},
            new String[] {"0x00a9a87d"}, new String[] {"0x0092ba44"},
            6, 22, 2,
            "a300be326f8c70402c66a1221a43fb14d36e560614457b17b8ce1021e6f58568")
    };

    private Listing listing;
    private FunctionManager functions;
    private ReferenceManager references;

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException(
                "Usage: RecoverP1bAddressTakenFunctions.java <output.tsv>");
        }
        if (!RETAIL_MD5.equalsIgnoreCase(currentProgram.getExecutableMD5())) {
            throw new IllegalStateException("program is not the pinned SHIFT retail executable");
        }

        listing = currentProgram.getListing();
        functions = currentProgram.getFunctionManager();
        references = currentProgram.getReferenceManager();
        List<String> results = new ArrayList<>();
        Set<String> seenEntries = new HashSet<>();
        int transaction = currentProgram.startTransaction("Recover address-taken orphan functions");
        boolean commit = false;
        try {
            for (Candidate candidate : CANDIDATES) {
                monitor.checkCancelled();
                Address entry = parse(candidate.entry);
                Address end = parse(candidate.end);
                if (!seenEntries.add(entry.toString())) {
                    throw new IllegalStateException("duplicate function entry: " + candidate.entry);
                }
                if (functions.getFunctionAt(entry) != null || functions.getFunctionContaining(entry) != null) {
                    throw new IllegalStateException("entry already belongs to a function: " + candidate.entry);
                }
                verifyEntryReferences(candidate, entry);
                verifyPrecedingBoundary(candidate, entry);

                Instruction last = listing.getInstructionAt(end);
                if (last == null || !last.getMnemonicString().toUpperCase().startsWith(candidate.terminalMnemonic)) {
                    throw new IllegalStateException("unexpected terminal instruction at " + candidate.end);
                }
                AddressSet body = new AddressSet(entry, last.getMaxAddress());
                Address expected = entry;
                int instructionCount = 0;
                int pcodeInstructionCount = 0;
                int callInstructionCount = 0;
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
                    MemoryBlock block = currentProgram.getMemory().getBlock(instruction.getAddress());
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
                    || pcodeInstructionCount != candidate.instructionCount
                    || body.getNumAddresses() != candidate.bodyBytes
                    || callInstructionCount != candidate.callInstructionCount
                    || !candidate.bodySha256.equals(bodyHash)) {
                    throw new IllegalStateException("bounded body facts drifted at " + candidate.entry);
                }
                verifyCallsites(candidate);

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
                results.add("0x" + entryText + "\t" + function.getName() + "\t" + candidate.end + "\t"
                    + candidate.bodyBytes + "\t" + instructionCount + "\t" + pcodeInstructionCount + "\t"
                    + callInstructionCount + "\t" + bodyHash + "\t" + String.join(";", candidate.callsites));
            }
            commit = true;
        } finally {
            currentProgram.endTransaction(transaction, commit);
        }

        File output = new File(args[0]).getAbsoluteFile();
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("cannot create output directory");
        }
        try (BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(output), StandardCharsets.UTF_8))) {
            writer.write("entry\tfunction_name\tend\tbody_bytes\tinstruction_count\tpcode_instruction_count\tcall_instruction_count\tbody_sha256\towned_callsites");
            writer.newLine();
            for (String row : results) {
                writer.write(row);
                writer.newLine();
            }
        }
        println("Recovered " + results.size() + " address-taken orphan functions -> " + output);
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
        if (!foundSources.equals(expectedSources)) {
            throw new IllegalStateException("missing exact address-taken reference at " + candidate.entry);
        }
    }

    private void verifyPrecedingBoundary(Candidate candidate, Address entry) {
        Instruction previous = listing.getInstructionBefore(entry);
        if (previous == null || !previous.getMaxAddress().add(1).equals(entry)) {
            throw new IllegalStateException("function entry is not adjacent to its preceding terminator: " + candidate.entry);
        }
        String mnemonic = previous.getMnemonicString().toUpperCase();
        if (candidate.precedingBoundaryTarget != null) {
            if (!mnemonic.startsWith("JMP")) {
                throw new IllegalStateException("second table entry is not separated by its exact tail transfer");
            }
            Address[] flows = previous.getFlows();
            if (flows.length != 1 || !flows[0].equals(parse(candidate.precedingBoundaryTarget))) {
                throw new IllegalStateException("unexpected preceding tail-transfer target");
            }
        } else if (!mnemonic.startsWith("RET")) {
            throw new IllegalStateException("function entry does not immediately follow a RET: " + candidate.entry);
        }
    }

    private void verifyCallsites(Candidate candidate) {
        if (candidate.callsites.length != candidate.targets.length) {
            throw new IllegalStateException("callsite/target plan mismatch: " + candidate.entry);
        }
        for (int i = 0; i < candidate.callsites.length; i++) {
            Address callsite = parse(candidate.callsites[i]);
            Address target = parse(candidate.targets[i]);
            Instruction instruction = listing.getInstructionAt(callsite);
            if (instruction == null || !instruction.getFlowType().isCall()) {
                throw new IllegalStateException("expected direct call instruction at " + candidate.callsites[i]);
            }
            boolean exactCall = false;
            for (Reference reference : instruction.getReferencesFrom()) {
                if (reference.getReferenceType().isCall() && reference.getToAddress().equals(target)) exactCall = true;
            }
            if (!exactCall) {
                throw new IllegalStateException("missing exact call reference at " + candidate.callsites[i]);
            }
        }
    }

    private Address parse(String token) {
        String value = token.trim();
        if (value.startsWith("0x") || value.startsWith("0X")) value = value.substring(2);
        return toAddr(Long.parseUnsignedLong(value, 16));
    }

    private String toHex(byte[] bytes) {
        StringBuilder result = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) result.append(String.format("%02x", value & 0xff));
        return result.toString();
    }

    private static final class Candidate {
        private final String entry;
        private final String end;
        private final String terminalMnemonic;
        private final String terminalTarget;
        private final String precedingBoundaryTarget;
        private final String[] referenceSources;
        private final String[] callsites;
        private final String[] targets;
        private final int instructionCount;
        private final int bodyBytes;
        private final int callInstructionCount;
        private final String bodySha256;

        private Candidate(
                String entry,
                String end,
                String terminalMnemonic,
                String terminalTarget,
                String precedingBoundaryTarget,
                String[] referenceSources,
                String[] callsites,
                String[] targets,
                int instructionCount,
                int bodyBytes,
                int callInstructionCount,
                String bodySha256) {
            this.entry = entry;
            this.end = end;
            this.terminalMnemonic = terminalMnemonic;
            this.terminalTarget = terminalTarget;
            this.precedingBoundaryTarget = precedingBoundaryTarget;
            this.referenceSources = referenceSources;
            this.callsites = callsites;
            this.targets = targets;
            this.instructionCount = instructionCount;
            this.bodyBytes = bodyBytes;
            this.callInstructionCount = callInstructionCount;
            this.bodySha256 = bodySha256;
        }
    }
}
