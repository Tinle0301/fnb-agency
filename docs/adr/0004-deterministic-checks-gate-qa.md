# Deterministic checks can fail QA on their own

Health claims, alcohol marketing to minors, placeholders, invalid colors and failing contrast are checked in code before the QA Reviewer runs. A blocker from these checks fails the gate even if the model passes the report. A model reviewer misses things at random; regulated-claim mistakes are the ones a client cannot afford, so they get a check that never has an off day.
