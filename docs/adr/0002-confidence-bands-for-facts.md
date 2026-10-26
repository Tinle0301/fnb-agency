# Facts are saved by confidence band, and people break ties

A smaller, cheaper model extracts facts after final sign-off. Facts at or above 0.85 become active, 0.60 to 0.85 wait as pending for a person, and anything lower is dropped. Re-extracting a fact never lowers its confidence or status, and a fact a person rejected is never re-added. We chose bands over a single threshold because a single threshold either lets doubtful facts in or throws useful ones away; the middle band costs a click instead.
