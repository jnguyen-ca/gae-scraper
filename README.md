# wettpoint_tip_stake Values
wettpoint_tip_stake is a property of Tip and is one of the main properties used for analysis.
Its range of value is 10 - (-10), and is defined as such:
* x = 0
> 1. Event has not appeared on the table and the table has gone past it
> 2. Either event is not H2H-allowed or is and has no stake value
* x < 0
> 1. Event has not appeared on the table, but the table has not yet gone past it
> 2. Event is H2H-allowed and has a team value, total value, and stake value
* x >= 1
> 1. Event has appeared on the table
* 0 < x < 1
> 1. Event has not appeared on the table and the table has gone past it
> 2. Event is H2H-allowed and has a stake value