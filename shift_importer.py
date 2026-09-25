    p.set_defaults(fn=cmd_camera_catalog)

    p = sp.add_parser("flat-runtime", help="decode a copied runtime FLAT tree body")
    p.add_argument("input", help="FLAT body starting at the bytes passed to FUN_0068a8b0")
    p.add_argument("output", help="SHIFT.FLATRuntime/1 JSON output")
    p.add_argument("--allow-partial", action="store_true")
    p.add_argument("--max-depth", type=int, default=64)
    p.set_defaults(fn=cmd_flat_runtime)

    p = sp.add_parser("color-evidence-corpus", help="aggregate multiple COLOR ABI evidence JSON reports without selecting an ABI")
    p.add_argument("input", nargs="+", help="evidence JSON file(s) or directories")
    p.add_argument("output", help="SHIFT.ColorABICorpusEvidence/1 JSON output")
    p.set_defaults(fn=cmd_color_evidence_corpus)

    p = sp.add_parser("color-evidence-resource", help="extract a MEB from BFF and report COLOR0/COLOR1 candidates")
    p.add_argument("archive", help="BFF archive")