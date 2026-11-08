# Files of revision 4.5 (the SKY130 test chip of 12 October 2026), quoted by section 25 of tests/test_claims.py

Rebuilt on 7 November 2026. The archive made when revision 4.5 was closed (4 November) did not reach the owner's PC before
the cloud sandbox holding it was reclaimed, so it was rebuilt from the copies on the PC:

- `sky130_chip/*`, `formal.log`, `rtl_mutation*.json`: the repository synced on 12 October 2026 (`sync_final.tgz`, 11:15),
  with the sign-off files of the same day laid over it (`final_sync.tgz`, 16:20). Nothing in sky130_chip changed after that
  until revision 4.6 (4 November).
- `sky130_chip/top_signoff.json`, `top_layout.json`, `antenna_crosscheck.json`: PC batch 22 (`b22.tgz`, 12 October 15:56), the
  sign-off of the final GDS (md5 37a6fb42...); the copies in the 11:15 sync were of an earlier GDS.
- `formal_faults.json`: the run of 10 October (`repo_sync.tgz`, 9 of 9 faults caught). The proofs' faults did not change in
  revision 4.5 (its changes were to the chip, not to `rtl/tcim_core.sv`), and the regression of 12 October did not re-run them.
- `sky130_chip/tcim_chip_digital.v`: the place-and-route source of revision 4.5 (kept since 4 November).
The layout of revision 4.5 is in `chip/sky130/caravan_rev45` (GDS md5 37a6fb42..., equal to the md5 in `sky130_chip/precheck.json`)
and `flow/orfs/outdig_rev45` (only `6_final.def` in the sandbox copy).
