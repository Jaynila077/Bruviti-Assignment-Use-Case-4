# NOTES.md

## Decisions worth flagging

- Figuring out which days a seat was actually held happens in one place (`seat_calendar.py`), once, not separately for each metric. It merges all the seat rows for a (user, tool) pair into one clean set of days, even if the rows overlap or repeat. Every number, licensed users, active users, spend, idle spend is built off that same set. That's the main reason the people-numbers and the money-numbers can't end up disagreeing with each other.

- When two seat rows for the same (user, tool) genuinely overlap on a day, I charge whichever price is higher for that day (see DATA.md #7). I want to be upfront that this is a reasonable guess, not something the brief actually tells you to do. If this needed to be exact, I'd go back and ask whether it makes more sense to just use whichever seat was granted more recently (closer to how a real tier upgrade would work) instead of always picking the higher price.

- The seat calendar gets built once when the app starts, not freshly on every request. Doesn't matter much at this data size, but it means the app isn't redoing the same work over and over if someone hits the API repeatedly with different dates/orgs.

- Since the grading data has problems I can't see, the loader never refuses to start because of a bad row. It skips the row and logs a warning instead (details in DATA.md #10). The downside is a broken row quietly drops out of the numbers, so the warnings in the startup log are worth a look.

## What I didn't do

- No caching for specific queries. Didn't need it, everything's well under a second even for a company-wide query over a long window.
- No real logging or metrics, just the "loaded X rows" lines at startup, plus a warning for any bad row the loader skips. Felt like overkill to do more for a take-home.
- The UI is deliberately very simple, a form, a summary, a table. It's there to show the API works, not to look like a finished product.

## What I'd do with more time

- Figure out the "right" rule for the overlapping-price case instead of just going with higher-price, once I actually know what it's supposed to mean.
- Write some tests that throw random seat/event data at the engine and check things that should always be true no matter what like, licensed users never being less than active users, or per-tool spend always adding up to the total spend, instead of only testing against a few examples I picked by hand. I checked this by hand against the real data and it held up, but that's not the same as having a test that checks it automatically.
