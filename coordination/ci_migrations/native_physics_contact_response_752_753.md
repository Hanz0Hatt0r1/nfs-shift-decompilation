# Native physics contact-response CI migration: Phase 752 + 753

Historical workflows `native-physics-phase752.yml` and `native-physics-phase753.yml` are replaced by the stable `native-physics-contact-response.yml` family.

The replacement uses the union of both historical trigger surfaces and executes both Python regressions, both evidence-contract checks, all three native targets required by the two workflows, the corresponding CTest set, and both native report validations.

The machine-readable parity contract is `native_physics_contact_response_752_753.json`. No semantic gate or external-provider count changes are part of this migration.
