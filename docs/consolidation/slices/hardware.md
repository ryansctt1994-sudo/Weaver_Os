# HARDWARE — bounded review-only extraction

**Parent**: #134 `de15972b4fc29ec0a21f521ccf641946270ffcbf`. **Combined source**: #135 `f65fa54c56341a8d5508af728fc773055afa1cd2`. All extracted source files are exact Git blobs from #135.

**Non-claims**: Arty wrapper, reset/debounce simulation and physical reproduction templates. Simulation and design notes only; no synthesis timing closure, FPGA programming, or physical behavior is claimed.

## Exact source/target provenance

| Path | Source commit | Target SHA-256 or source identity |
|---|---|---|
| `hardware/lucifer_latch/arty_a7/README.md` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `3074c45f622633a31133fa456ce2c3749ff59412002804b3c0607631f57689ed` |
| `hardware/lucifer_latch/arty_a7/arty_a7_35.xdc` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `d29de2ce192028eaa25ee44c3b7a4a26cf7324cc116765a7b93dae450e5770c4` |
| `hardware/lucifer_latch/arty_a7/build.tcl` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `cf9041433b26c9e30c5c2e59f601feecc7aa565f5fe84d998971af4b250a6f4e` |
| `hardware/lucifer_latch/arty_a7/lucifer_arty_a7.v` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `b141eeb3a4b8705e6d6f0b840da6702498ba9b5d9d3e7f4194cc95aec34e8e4b` |
| `hardware/lucifer_latch/arty_a7/program.tcl` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `82a552cc64e6cb760ef74dfdb6350c74803e7cbb4c23bfde732a3603398a7b5e` |
| `hardware/lucifer_latch/arty_a7/qualification/PHYSICAL_RUN_PROTOCOL.md` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `26acaf934cdda8a89c1de2c879a6d16d6d086dfbc89c211c460630653cb5604f` |
| `hardware/lucifer_latch/arty_a7/qualification/PUBLIC_WITNESS_POLICY.md` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `d3edeb737d88fbb3ae40851f23c0de407521c317bf93db5626c821a6d29d68e3` |
| `hardware/lucifer_latch/arty_a7/qualification/README.md` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `de9c78fc9e8261921112fff2efb9ebc0bb082b768a04108518ab56662260048c` |
| `hardware/lucifer_latch/arty_a7/qualification/SRAM_AND_PERMANENCE.md` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `2f0d9a3488bb65e8d807e026ef871cabe5fd764633ca52a12686ec8d90116bbe` |
| `hardware/lucifer_latch/arty_a7/qualification/packet.sha256` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `d668739d2db6c219a7bb6373807254f800434195f8a835ba38e67aba53bea8bd` |
| `hardware/lucifer_latch/arty_a7/qualification/templates/authority-roster.json` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `496d997298454d32a2c7b69e2a461c8fa0a16cae70ac06cdbaa12c54c1c0f214` |
| `hardware/lucifer_latch/arty_a7/qualification/templates/outside-reproduction-receipt.json` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `cb453419db71b602fcbc20e0f9098131aeb3a1e2383c4533116555127b9d4a65` |
| `hardware/lucifer_latch/arty_a7/qualification/templates/physical-measurements.csv` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `ddbcb5435634d4457d4297b6b40bc59f1cd254e99dafd6e325ba818f38398042` |
| `hardware/lucifer_latch/arty_a7/qualification/templates/quorum-evaluation.json` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `f445900ac396fe0e3d428b76633f4537901980764210087c0c313373a6a95308` |
| `hardware/lucifer_latch/arty_a7/qualification/templates/run-manifest.json` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `356e9ee90b8e86dfcb4f5800940f6b0cb8165ebc0b5f0cbf2f4f4e4f139f63ee` |
| `hardware/lucifer_latch/arty_a7/qualification/templates/timing-receipt.json` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `cfc0a1a5ade3cde2591db3adfe57f238560ba9d6967feb7df2663de8f9f92d14` |
| `hardware/lucifer_latch/arty_a7/sync_debounce.v` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `68726d4a22e425940cbc693a0d5757c02d27a4bb17d520a2fa260efd686bd00f` |
| `hardware/lucifer_latch/arty_a7/tb_arty_a7.v` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `f832fc2058d2ba68299913661aa707e8a7ccd46c91349bf4e1004b9a61641afd` |
| `hardware/lucifer_latch/arty_a7/tb_debounce_default.v` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `e0374ff98c458942389d56dcf104d028484541fc81d093473efb13e0a8d56d39` |
| `hardware/lucifer_latch/arty_a7/tb_startup_reset.v` | `e943fcaa73f9c2cd8f9aa471ce160cc24daddb9c` | `b387e852fc6ce3e697b91d20c75d6299a0e42cb2c79331d03d27cf9e79bf9de9` |
| `tools/consolidation/__init__.py` | Derived at #135 `f65fa54c5634` | Git blob identity pinned |
| `tools/consolidation/check_hardware.py` | Derived at #135 `f65fa54c5634` | Git blob identity pinned |

## Required verification

```sh
sudo apt-get install iverilog
python -m tools.consolidation.check_hardware
python tools/hw_negative_controls.py
python -m tools.gen_latch_vectors --check
python -m tools.verify_all
```

Acceptance requires actual logs for this exact head, negative controls, and review of all active imports and license files. This branch intentionally does not carry unrelated tools or eight archival ZIP snapshots, which remain frozen in #135. Recheck on the final integrated tree; no source's previous CI results transfer to this SHA.

**E2 · W0 · O0 WITHHELD · V008 HOLD · DO NOT MERGE · PRODUCTION PROHIBITED.**
