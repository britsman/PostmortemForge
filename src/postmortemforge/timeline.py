"""The ordered timeline model.

A Timeline is the aligned, merged event stream plus the correlation features and
links found over it. It is the single structure the draft writer and the report
renderer read from, so the incident is described once and consumed many ways.

Time is presented as minutes elapsed from the first event, which is the natural
axis for a postmortem and keeps the diagram and the prose using the same units.
