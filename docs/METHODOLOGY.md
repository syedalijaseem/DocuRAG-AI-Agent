# Development Working Methodology

This document outlines the standardized approach for developing each milestone in the DocuRAG project.

---

## Milestone Folder Structure

Each milestone has its own folder under `docs/` with the following standardized structure:

```
docs/
├── m0-authentication/
│   ├── requirements.md          # Functional & non-functional requirements
│   ├── tasks.md                 # Detailed task breakdown with checkboxes
│   └── walkthrough.md           # Post-completion: development summary & proof
│
├── m1-core-data-model/
│   ├── requirements.md
│   ├── tasks.md
│   └── walkthrough.md
│
├── m2-ingestion-pipeline/
│   └── ...
│
└── implementation_plan.md       # Master plan with ER diagram & milestones
```

---

## Development Lifecycle

### Phase 1: Planning

1. **Review Master Plan**

   - Read `implementation_plan.md`
   - Understand the ER diagram and relationships
   - Identify dependencies from previous milestones

2. **Create Requirements Document**

   - Define functional requirements (what the system must do)
   - Define non-functional requirements (quality attributes)
   - Specify acceptance criteria for each requirement

3. **Create Tasks Document**

   - Break down requirements into specific, actionable tasks
   - Estimate effort for each task
   - Identify task dependencies
   - Use checkbox format for progress tracking

4. **User Review**
   - Submit requirements and tasks for user approval
   - Incorporate feedback
   - Get sign-off before proceeding

### Phase 2: Execution

1. **Create Feature Branch**

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/m<N>-<milestone-name>
   ```

2. **Implement Tasks**

   - Work through tasks in dependency order
   - Update `tasks.md` with progress ([ ] → [/] → [x])
   - Commit frequently with descriptive messages

3. **Testing**

   - Write unit tests for each component
   - Run comprehensive test suite
   - Cover the 9 quality aspects:
     - Security
     - Robustness
     - Scalability
     - Accessibility
     - Optimization
     - UI
     - UX
     - Reliability
     - Efficiency

4. **Push Regularly**
   ```bash
   git push origin feature/m<N>-<milestone-name>
   ```

### Phase 3: Verification

1. **Run All Tests**

   - Backend: `uv run pytest tests/ -v`
   - Frontend: `npm run build`
   - Browser: Manual UI testing

2. **Create Walkthrough Document**

   - Summarize what was implemented
   - Document key architectural decisions
   - Include screenshots/recordings of UI changes
   - List all tests and their results
   - Note any deviations from the original plan

3. **User Review**
   - Present walkthrough for final approval
   - Address any concerns

### Phase 4: Completion

1. **Final Commit**

   - Ensure all tasks are marked complete
   - Clean up any TODO comments

2. **Merge to Main**

   ```bash
   git checkout main
   git pull origin main
   git merge feature/m<N>-<milestone-name> --no-ff
   git push origin main
   ```

3. **Start Next Milestone**
   - Create new feature branch for next milestone
   - Begin Phase 1 again

---

## Quality Checklist (9 Aspects)

Before completing any milestone, verify:

| #   | Aspect            | Questions to Answer                                             |
| --- | ----------------- | --------------------------------------------------------------- |
| 1   | **Security**      | Are inputs validated? Is data encrypted? Are there auth checks? |
| 2   | **Robustness**    | Does it handle errors gracefully? Are edge cases covered?       |
| 3   | **Scalability**   | Can it handle more users/data? Are there bottlenecks?           |
| 4   | **Accessibility** | Are there proper labels? Is keyboard navigation working?        |
| 5   | **Optimization**  | Are queries efficient? Is there unnecessary computation?        |
| 6   | **UI**            | Does it look polished? Is the design consistent?                |
| 7   | **UX**            | Is the flow intuitive? Are error messages helpful?              |
| 8   | **Reliability**   | Does it work consistently? Are there race conditions?           |
| 9   | **Efficiency**    | Are resources used wisely? Is code maintainable?                |

---

## Commit Message Format

Use conventional commit format:

```
<type>(scope): <description>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**

```
feat(auth): add Google OAuth login endpoint
fix(upload): handle PDF with empty pages
docs(m1): create requirements specification
test(auth): add rate limiting test cases
```

---

## Branch Naming

```
feature/m<N>-<short-description>
```

**Examples:**

- `feature/m0-authentication`
- `feature/m1-core-data-model`
- `feature/m2-ingestion-pipeline`

---

## Document Templates

### requirements.md Template

```markdown
# M<N>: <Milestone Name> - Requirements Specification

## Overview

[Brief description of the milestone goal]

## Functional Requirements

### FR-1: [Requirement Name]

- **Description:** [What the system must do]
- **Acceptance Criteria:** [Testable conditions]

## Non-Functional Requirements

### NFR-1: [Requirement Name]

- **Category:** [Security/Performance/Usability/etc.]
- **Description:** [Quality attribute]
- **Metric:** [Measurable target]
```

### tasks.md Template

```markdown
# M<N>: <Milestone Name> - Task Breakdown

## Overview

[Brief description]

## Tasks

### Backend

- [ ] Task 1 (~Xh)
  - [ ] Subtask 1.1
  - [ ] Subtask 1.2

### Frontend

- [ ] Task 2 (~Xh)

### Testing

- [ ] Task 3 (~Xh)

## Dependencies

- Requires: [Previous milestone or external dependency]

## Estimated Total: X-Y days
```

---

## Review Checklist

Before requesting user review:

- [ ] All tests passing
- [ ] No TypeScript/lint errors
- [ ] Code is documented
- [ ] Requirements document complete
- [ ] Tasks document complete
- [ ] 9 quality aspects verified
