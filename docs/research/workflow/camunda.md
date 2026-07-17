# Camunda

**What it is:** Open-source/enterprise BPMN process orchestration engine (Zeebe) plus DMN decision engine and Tasklist UI — the reference implementation for human-task assignment, approval chains, and business-rule tables as OMG standards.
**Axis:** workflow, enterprise.
**Depth:** deep.

## Products & surfaces

| Product | What it is |
|---|---|
| **Zeebe** | The BPMN process engine — executes process definitions, creates/tracks user task instances. |
| **Tasklist** | Human task inbox — built-in web app, or build your own via the Tasklist API. |
| **DMN engine** | Executes decision tables (business rules) as a distinct artifact from process code. |
| **Modeler** | BPMN/DMN/Forms visual design tool. |
| **Optimize** | Process analytics on top of task/process lifecycle events. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| User task lifecycle: create → claim → complete | Explicit claim step before work starts | yes |
| Assignee / candidate-users / candidate-groups | Three-parameter assignment model, settable simultaneously | yes |
| Assign to groups, not individuals | Default guidance — avoid single points of failure | yes |
| Delegation with owner/assignee split | Delegate resolves and passes back; original assignee remembered as owner | yes |
| Four-eyes principle enforcement | Explicit "not equal" gateway check that the two approvers differ | yes |
| Due date / priority, modifiable post-deployment | Task metadata editable even on running instances | yes |
| Tasklist: built-in / custom / third-party sync | Three explicit integration modes | yes |
| Tasklist V2 authz regression | Candidate users/groups no longer gate visibility; authz collapsed to process-definition level | cautionary |
| DMN hit policies (Unique/First/Any/Collect+) | Standardized semantics for what happens when multiple rules match | yes |
| FEEL | Standard, business-readable, sandboxed expression language | yes |
| User task assignment via DMN table | "Who approves this" resolved as a business rule, not hardcoded | yes |
| DMN Simulator | Test decision tables against sample input without deploying | maybe |

## Worth stealing

### User tasks: create → claim → complete, and why the claim step exists

Camunda's task lifecycle is deliberately three-phased, not two: a task instance is **created** (visible, unassigned or assigned), an individual **claims** it (explicitly picking it up from a pool), then **completes** it. The claim step is the specific mechanism that *"avoid[s] different people working on the same task at the same time"* — without it, a shared task list has no way to signal "someone is already working on this" short of external coordination. The lifecycle also supports **return** (hand a claimed task back to the pool) and delegation (below) as first-class transitions, not just create/complete.

### Assign to groups, not individuals — the default, not the exception

Camunda's own best-practice guidance states this as a general rule: *"you should assign human tasks, like user tasks or manual tasks, in your business process to groups of people instead of specific individuals"* — this avoids bottlenecks (*"high workloads on single individuals or employees being on sick leave"*). The mechanism is a **three-parameter model, settable simultaneously**: `assignee` (a specific person who must do it), `candidateUsers` (a named list of eligible people), `candidateGroups` (eligible groups). Members of a candidate group or list claim from the shared pool; only genuinely unique work gets a hardcoded `assignee`.

The design lesson generalizes past Camunda: **individual-assignment-first designs die on the first vacation.** A task-assignment model that only supports "assign to person X" has no answer for "person X is out" short of manual reassignment by someone who has to notice the block exists. The right default triple is assignee / candidate-users / candidate-groups, with candidate-groups as the common case and individual assignment reserved for work that is genuinely one-person-only.

### Delegation — the delegate resolves it and hands it back, with the original assignee as owner

Camunda's delegation semantics are specific and worth being deliberate about, because there's more than one valid model in the industry: *"When you delegate a task assigned to you using Camunda's `delegateTask` function, somebody else is supposed to resolve some of the work and then pass the task back to you by resolving it. The original assignee is remembered as the 'owner' of the task."* Concretely: `delegateTask(taskId, "gonzo")` makes "gonzo" the new assignee while the original assignee becomes the `owner`; when gonzo is done, `resolveTask()` returns it to the owner rather than completing it outright. Typical use case: information-gathering by a delegate ahead of a decision the owner still has to make.

**This differs from Salesforce's delegate-can-approve semantic**, where a delegate approves *on behalf of* the original approver and the task is simply done. Camunda's model keeps the original owner as the final decision-maker; the delegate's action doesn't itself close the task. Pick one deliberately — they imply different audit stories ("who actually approved this") and different failure modes if a delegate never gets around to resolving.

### Four-eyes principle — the second approver must literally not be the first

Segregation-of-duties (SoD) is a hard audit requirement in regulated enterprises, and Camunda's guidance treats it as something the *workflow engine* must enforce, not something to hope reviewers self-police: *"the two or more tasks needed to ultimately approve a request must not be completed by one and the same person. When executing such patterns, you must enforce that with the workflow engine."* The concrete mechanism is a gateway that runs an explicit **"does not equal"** check comparing the first reviewer's identity to the second reviewer's identity before allowing the second approval task to be assigned/completed — i.e., SoD is implemented as a data condition on the process, not a UI hint or a policy document.

### Due dates, overdue tags, priority — mutable even on running instances

Task metadata (due date, priority) is settable at task-creation time via static values or expressions, and — per Camunda's task lifecycle model — **modifiable after deployment, even while the process instance is running**, via the API (change assignment, due date, or other task attributes on an in-flight instance). This matters because real organizations reassign work in flight constantly — a manager going on leave, a priority escalation, a due-date extension — and a task model that only supports configuring these values at task-creation time forces a workaround (cancel and recreate the task) for what should be a routine operational action.

### Tasklist — three integration modes, named explicitly

Camunda names three distinct ways to expose human tasks to end users, rather than assuming one: **(1)** the built-in Tasklist web app, **(2)** a **custom application built against the Tasklist API** (query tasks, filter by assignee/candidate-group, render your own UI, following your own style guide), **(3)** **sync to a third-party system** an organization already has rolled out — requiring your own sync logic to create/complete/cancel tasks on both sides and transfer business data back and forth. Naming all three as legitimate, supported paths (rather than treating "use our UI" as the only real option) is itself the useful design precedent — task visibility is a UX problem separable from the process engine, and enterprises frequently already have a task inbox they don't want to abandon.

**Caution: the Tasklist V2 regression.** As of Camunda 8.8 (V2 default), *"candidate users and candidate groups are not evaluated by Tasklist for task visibility or assignment"* — V2 authorization is **process-definition-level only**, meaning anyone with access to a process definition can see all its tasks, regardless of candidate-group/user restrictions that worked in V1. This is documented by Camunda itself as a V1→V2 capability gap, not a hypothetical risk. The transferable lesson: **task-level visibility must be a first-class part of the authorization model from the start** — retrofitting fine-grained task visibility onto a coarser, resource-level authz system (here, "can you see this process definition") is the kind of regression that's easy to ship silently, because the coarse check still returns *something* rather than an obvious failure.

### DMN — decision tables as a versioned, business-editable artifact

DMN decision tables are an OMG standard, explicitly positioned as living **outside code**: *"task assignment logic can become quite elaborate... DMN decision tables are an excellent tool to manage such rules outside of code, in a business user-friendly way."* They're **versioned separately from the process/code that calls them** — a business analyst can update a rules table and redeploy it without a code change or redeploying the calling process.

**Hit policies are the semantics of the table, not decoration.** Camunda's own framing: *"Different hit policies do not only lead to different results, but typically also require different modes of thinking and reason about the meaning of the entire table."* The four core policies:
- **Unique** — rules must not overlap; exactly one may match (the default). This is the policy that lets you assert "these cases are mutually exclusive" and have the engine catch a violation.
- **First** — top-down; multiple rules may match, the first one wins. This is the only policy naive rule engines tend to ship, and it silently discards the ability to express "these must not overlap" — a table author can accidentally rely on row order without the engine ever telling them two rules conflict.
- **Any** — multiple rules may match, but only if they all agree on the output; disagreement is an error, not a silent pick.
- **Collect** (plus aggregation variants Sum/Min/Max/Count) — don't care about order or overlap at all; gather every matching rule's output into a list. This is exactly the policy used for the "assignee / candidateUsers / candidateGroups" task-assignment table pattern below, since a task can validly be routed to a combination of eligible people/groups.

The reusable point: a rules-table feature that only supports First-hit-wins has quietly given up the validation properties (mutual exclusivity, agreement-checking) that make DMN trustworthy as a business-rule surface — hit policy choice is a semantic decision about what "the table means," and offering only one policy forecloses expressing several distinct, common business-rule shapes.

### FEEL — and the Go-native alternative

FEEL (Friendly Enough Expression Language) is the OMG-standard expression language embedded in DMN tables, BPMN conditions, and Forms — deliberately designed to read like a sentence rather than code, so a *"process analyst friendly"* non-engineer can write and audit the logic driving a decision table. It's sandboxed by construction (a decision-table expression language, not a general-purpose scripting escape hatch) — the same safety property that makes CEL (Common Expression Language) attractive as the Go-native equivalent: both are intentionally restricted, non-Turing-complete expression languages designed to be safely embedded and evaluated inside a host application without a full interpreter's attack surface.

### User task assignment as a DMN table, not hardcoded logic

Camunda's documented pattern for elaborate assignment logic (insurance claims, multi-tier approval routing) is a **business-rule task that evaluates a DMN decision table configured with `Collect` hit policy**, producing up to three outputs per matching rule (assignee, candidateUsers, candidateGroups); the results are mapped via FEEL expressions onto the actual task-assignment fields. The point generalizes past Camunda: **"who approves this?" is a business rule that changes by amount, region, or department** — exactly the kind of logic that should live in a business-editable, separately-versioned table rather than hardcoded in process/application code, for the same reason any other frequently-changing business rule benefits from being externalized.

### DMN Simulator — test a table without deploying it

A web tool (and companion JUnit/plugin tooling) that lets you enter sample input values and immediately see which rule(s) fired and what output resulted, highlighting the matched row in the table — a fast validation loop for a business user editing a decision table, separate from writing a full test suite in code.

## Worth avoiding

**BPMN-as-procurement-requirement misses the actual requirement underneath.** Enterprise procurement processes sometimes name BPMN specifically as a checkbox. But the real requirement being reached for is *legibility to non-engineers* — a process diagram that a compliance officer, auditor, or business stakeholder can read and validate without engineering translation. BPMN is *a* way to satisfy that (an OMG standard, tool-portable, with broad enterprise tooling support), but treating "must be BPMN" as the literal requirement rather than "must be legible to non-engineers" risks over-indexing on notation compliance instead of the actual goal.

**The Tasklist V2 authorization regression** (above) is the sharper cautionary tale: a real product shipped a new default mode that silently dropped a security property (task-level visibility via candidate users/groups) in favor of a coarser one (process-definition-level authz), and it's documented as a known gap rather than reverted. Fine-grained authorization is easy to lose in a rewrite if it isn't treated as a hard invariant the new implementation must preserve.

## Facts & figures

- BPMN is an OMG standard, also published as ISO/IEC 19510.
- DMN hit policies: 7 total in the OMG spec (Unique, Any, Priority, First, Collect, Output order, Rule order); Collect additionally supports 4 aggregation variants (Sum, Min, Max, Count).
- Tasklist V2 became the default mode as of Camunda 8.8 (vendor docs); the candidate-users/groups visibility gap is documented as V1-only functionality.

## Sources

- [User task lifecycle](https://docs.camunda.io/docs/apis-tools/frontend-development/task-applications/user-task-lifecycle/) · [User tasks (Modeler)](https://docs.camunda.io/docs/components/modeler/bpmn/user-tasks/) · [Camunda Best Practices: Managing the Task Lifecycle](https://camunda.com/best-practices/managing-the-task-lifecycle/)
- [Understanding human task management](https://docs.camunda.io/docs/components/best-practices/architecture/understanding-human-tasks-management/)
- [DelegateTask Javadoc](https://docs.camunda.org/javadoc/camunda-bpm-platform/7.22/org/camunda/bpm/engine/delegate/DelegateTask.html)
- [Four eyes principle forum thread](https://forum.camunda.io/t/four-eyes-principle-revoke-authorization/10823) · [Modeling with situation patterns](https://unsupported.docs.camunda.io/8.3/docs/components/best-practices/modeling/modeling-with-situation-patterns/)
- [User task access restrictions](https://docs.camunda.io/docs/components/tasklist/user-task-access-restrictions/) · [Camunda 8.8 Tasklist API V2 forum thread](https://forum.camunda.io/t/camunda-8-8-user-tasks-access-restriction-tasklist-api-v2/65664) · [Enhancing Tasklist Security blog](https://camunda.com/blog/2023/12/enhancing-tasklist-security-user-groups-restrictions-user-tasks/)
- [Choosing the DMN hit policy](https://docs.camunda.io/docs/components/best-practices/modeling/choosing-the-dmn-hit-policy/)
- [What is FEEL?](https://docs.camunda.io/docs/components/modeler/feel/what-is-feel/) · [Using FEEL with Camunda 8](https://camunda.com/blog/2022/09/using-feel-with-camunda-8/)
- [Camunda BPM: User Task Assignment based on a DMN Decision Table](https://camunda.com/blog/2020/05/camunda-bpm-user-task-assignment-based-on-a-dmn-decision-table/)
- [DMN Simulator](https://consulting.camunda.com/dmn-simulator/) · [Testing DMN Decision Tables](https://camunda.com/blog/2016/01/testing-dmn/)
- [BPMN (OMG)](https://www.omg.org/bpmn/) · [About the BPMN 2.0 Specification](https://www.omg.org/spec/BPMN/2.0/About-BPMN)
- **Not directly verified:** whether due date/priority modification on a running instance is available identically across Camunda 7 and Camunda 8/Zeebe REST APIs — the general capability is documented, exact API parity was not exhaustively checked.
