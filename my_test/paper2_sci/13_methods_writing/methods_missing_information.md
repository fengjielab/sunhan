# Information requiring author verification

The following items were not recoverable from the collection commit, archived logs, or `03_clean_analysis/`. They must not be completed from memory without supporting records. The list is divided by submission consequence.

## A. Must be confirmed before submission

1. **[NEEDS VERIFICATION: ethics approval or formal exemption]**  
   Required evidence: committee/institution name, approval or exemption identifier, and the wording permitted by the institution. Human-participant work cannot be submitted with this item unresolved.

2. **[NEEDS VERIFICATION: informed-consent procedure]**  
   Required evidence: whether written or oral informed consent was obtained, when it was obtained, and where the corresponding record is retained.

3. **[NEEDS VERIFICATION: minimum reproducible task description]**  
   Confirm the object-manipulation instruction, start and destination arrangement, required release/completion action, trial-reset procedure, and whether participants were instructed to prioritize speed, accuracy, or both. If the finer geometry and tolerances cannot be recovered, the verified minimum description must be supplied and the missing details disclosed as a limitation.

4. **[NEEDS VERIFICATION: journal-mandatory human-participant reporting]**  
   After the target journal is selected, check its required ethics, consent, participant eligibility, safety, and reporting-checklist fields. Do not infer eligibility criteria or adverse-event procedures if they were not documented.

5. **[NEEDS VERIFICATION: journal-mandatory declarations outside Methods]**  
   Funding, conflicts of interest, author contributions, data/code availability, and any required use-of-AI disclosure must be supplied by the authors according to the selected journal. These are submission requirements, not experimental methods, and are not added to the Methods draft here.

## B. If records cannot be found, disclose as limitations

1. **[NEEDS VERIFICATION: participant demographics and recruitment]**  
   Age or age range, sex/gender if collected, dominant hand, relevant robotics/teleoperation experience, recruitment route, and compensation. If these were never collected or are irrecoverable, state that the archived record did not preserve them.

2. **[NEEDS VERIFICATION: training/familiarization details]**  
   Whether training occurred, its duration and content, and whether training objects or trials overlapped the analyzed dataset. Do not reconstruct a training protocol from recollection alone.

3. **[NEEDS VERIFICATION: physical-object registry and placement]**  
   Object names, number of physical instances, mapping to soft/medium/hard, orientation, and placement. The current lineage preserves material category but not a unique `object_id`; material labels must not be converted into documented object identities.

4. **[NEEDS VERIFICATION: trial-order procedure]**  
   Whether mode/material/block order was randomized, counterbalanced, manually scheduled, or opportunistic. Timestamps reconstruct realized order but not the intended allocation procedure.

5. **[NEEDS VERIFICATION: operating system and control-computer metadata]**  
   OS/version, CPU, GPU, RAM, and whether vision inference ran on CPU or GPU.

6. **[NEEDS VERIFICATION: exact runtime software versions]**  
   Python, `panda_py`/libfranka, Force Dimension SDK, `pyrealsense2`, Ultralytics, and the model checksum.

7. **[NEEDS VERIFICATION: camera mounting and calibration]**  
   Camera pose, distance or field of view, and any camera-to-robot calibration. The audited acquisition code enabled only the RGB stream.

8. **[NEEDS VERIFICATION: unlogged external sensing hardware]**  
   The archived acquisition path contains only the Franka internal estimated external wrench. If the physical setup cannot be independently confirmed, retain the bounded statement about the audited path and do not claim that no external sensor was physically mounted.

9. **[NEEDS VERIFICATION: detailed reason for each 20260729 exclusion]**  
   The clean lineage documents the confirmed invalid-record/valid-replacement mapping but not a contemporaneous trial-specific failure narrative.

10. **[NEEDS VERIFICATION: finer task geometry, tolerances, rest, and practice details]**  
    Any part not recoverable after confirming the minimum task description in Section A should be reported as unavailable rather than invented.

## Safe manuscript wording if Section B records remain unavailable

- “Participant demographic and training details were not available in the archived experimental record.”
- “The archived dataset preserved material-category labels but not unique physical-object identifiers.”
- “The archived record did not document the prospective randomization or counterbalancing procedure.”
- “The recorded force signal was derived from the Franka internal estimated external wrench; no independent external force/torque measurement was present in the audited acquisition path.”
- “The exact runtime hardware and software versions were not preserved in the archived experimental metadata.”
