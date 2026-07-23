# Houston

Houston is an app builder for running many small apps together on shared, lightweight infrastructure.

Houston exists because building a small app involves a tedious amount of boilerplate and setup before it does anything interesting. 
Running through the normal playbook for building apps it currently involves this for me:

- terraform setup
    - provisioning an ec2 stack, (normally redis + python container + postgres + caddy)
    - setting up dkim provisioning
    - setting up dns routes for domains
    - Vercel deploy setup
- Copying over backend structure
    - openapi codegen pipeline
    - state machine
    - actions framework
    - auth framework (this will be shared platform tables)
    - various other abstractions ... 

The problem with this is twofold:
1. Much of the codebase is stuff that isn't actually going change project to project.
2. Even though the usage barely increases project to project, our costs scale linearly.


Houston aims to solve this:
1. These small projects will share infrastructure, a single database, single redis cache, single deploy task.
2. A shared reposiotry of easily importable abstractions


Houston is where a portfolio of small apps lives together. subway-status, marlin, arive, and pear are the first apps to run on it — each a standalone project today, each ported over and deployed on Houston.

Noting some issues I can imagine here:
- I don't want to worry about autoscaling with this, crucially we should not try to re-invent the wheel here. We're solving for the long tail of apps (a la serverless but not serverless)
- A lot of the magic of houston is distributing out pulumi / terraform in the right places.

## Who is it for?

A user of houston should be able to build and deploy a data heavy, backend heavy app with ease.

## what problem does it solve?

If i want to build a data heavy app at the moment, i get peanlized at the database level for either row count, or backend running cost. Supabase isn't a backend and cannot do complex business logic.
Backend and frontend providers are often split so i have to use vercel and railway together, if I want email that's again a whole independent service.

Users should be able to get all of these solved problems by default with maximum flexibility and minimal cost.


## Why am I building it now?

I've been making so many apps for friends that this is starting to both cost a lot AND im wasting time on infra and not domain work

## What does success look like?

Ultimate success is people building a customer facing application on this, that means using the stripe integration and even charging customers a saas fee VIA houston.
