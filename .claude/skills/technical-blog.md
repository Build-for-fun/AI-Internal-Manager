# Technical Blog Skill
**Description:** Generate a publishable technical blog post explaining recent code changes - what was built, why, challenges faced, and lessons learned.
**Usage:** /technical-blog [optional: topic focus]

**Trigger this skill when:**
- User says "blog", "write-up", "technical post", "explain this change"
- After completing a significant feature or refactor
- When user wants to share learnings externally
- After solving a challenging technical problem
- When preparing content for dev.to, Medium, personal blog, etc.

**Skip for:** Internal docs, minor fixes, config changes, routine updates

## Execution Workflow

### Step 1: Gather Change Context
**Run these commands in parallel:**
- `git log --oneline -10` - Recent commits for context
- `git diff --stat HEAD~5` - What changed recently (adjust range as needed)
- `git diff HEAD~5` - Actual code changes
- `git log --format="%s%n%b" -5` - Commit messages with bodies

**Identify:**
- The main narrative: What problem was solved?
- Key commits that tell the story
- Files with the most significant changes
- Any commit messages that hint at challenges or decisions

### Step 2: Understand the Technical Journey
**Read the most significant files** (top 3-5 from git diff):
- Focus on WHAT problem was solved and HOW
- Look for comments explaining "why" decisions were made
- Identify any clever solutions or non-obvious approaches
- Note any workarounds or trade-offs

**Extract the story elements:**
1. **The Problem:** What wasn't working or didn't exist?
2. **The Approach:** What options were considered?
3. **The Solution:** What was actually built?
4. **The Challenges:** What was harder than expected?
5. **The Outcome:** What's the result/impact?

### Step 3: Draft Blog Structure
**Create outline in `drafts/blog/YYYY-MM-DD_<topic>.md`:**

```markdown
# [Compelling Title - Problem or Solution Focused]

> One-sentence hook that makes readers want to continue

## The Problem

What I was trying to solve. Make it relatable.
- Context: What was the situation?
- Pain point: Why did this matter?
- Goal: What did success look like?

## First Attempts (Optional - if there were failed approaches)

What I tried first and why it didn't work.
This section humanizes the post and teaches readers what NOT to do.

## The Solution

### Key Insight
The "aha moment" or core idea that made it work.

### Implementation
Walk through the approach at a high level.

```[language]
// Key code snippet with comments
// Focus on the interesting parts, not boilerplate
```

### Why This Works
Explain the reasoning, not just the code.

## Challenges I Faced

### Challenge 1: [Name]
- What went wrong
- How I debugged/solved it
- What I learned

### Challenge 2: [Name]
(Repeat as needed - 2-3 max)

## Results

- Before vs After (if applicable)
- Performance improvements (if any)
- What's now possible that wasn't before

## Key Takeaways

1. **[Lesson 1]:** One sentence summary
2. **[Lesson 2]:** One sentence summary
3. **[Lesson 3]:** One sentence summary

## What's Next

Where this could go from here. Future improvements or related work.

---

*[Optional: Call to action, link to repo, invite discussion]*
```

### Step 4: Write the First Draft
**Use the Write tool to create the blog post.**

**Writing Guidelines:**

| Section | Length | Focus |
|---------|--------|-------|
| Title | 5-10 words | Problem or benefit focused, searchable |
| Hook | 1-2 sentences | Create curiosity or promise value |
| Problem | 2-3 paragraphs | Relatable, specific, sets stakes |
| Solution | 3-5 paragraphs + code | Clear explanation with key snippets |
| Challenges | 2-3 subsections | Honest, educational |
| Takeaways | 3-5 bullets | Actionable insights |

**Code Snippets:**
- Include only the interesting parts (10-30 lines max per snippet)
- Add comments explaining non-obvious logic
- Use syntax highlighting with language tags
- Show before/after when relevant

### Step 5: Add Technical Credibility
**Enhance with specifics:**
- Exact file paths where key logic lives
- Performance numbers if available
- Links to relevant docs or inspirations
- Git commit hashes for reference (optional)

**Add metadata block at top:**
```markdown
---
title: "[Title]"
date: YYYY-MM-DD
tags: [tag1, tag2, tag3]
summary: "One paragraph summary for SEO/previews"
---
```

### Step 6: Review and Polish
**Self-review checklist:**
- [ ] Title is compelling and searchable
- [ ] Opening hook grabs attention
- [ ] Problem is clearly stated
- [ ] Solution is explained, not just shown
- [ ] Code snippets are minimal but complete
- [ ] Challenges section is honest and educational
- [ ] Takeaways are actionable
- [ ] No sensitive data (API keys, internal URLs, etc.)
- [ ] Grammar and flow are clean

**Read the draft out loud** (mentally) - does it flow?

### Step 7: Present to User
**Show the user:**
1. Blog post title and summary
2. Estimated read time (words / 200)
3. Where the draft was saved
4. Key sections included

**Ask:**
- "Want me to adjust the tone (more technical / more casual)?"
- "Should I expand any section?"
- "Ready to export for [platform]?"

## Blog Post Types

### Type 1: "How I Built X"
- Focus: Implementation journey
- Audience: Developers who might build similar things
- Key sections: Problem, Approach, Code walkthrough, Lessons

### Type 2: "Solving X: A Deep Dive"
- Focus: Specific technical challenge
- Audience: Developers facing similar problems
- Key sections: Problem, Failed attempts, Solution, Why it works

### Type 3: "Why We Chose X Over Y"
- Focus: Decision making process
- Audience: Tech leads, architects
- Key sections: Requirements, Options considered, Trade-offs, Decision

### Type 4: "Lessons from Building X"
- Focus: Retrospective insights
- Audience: General developer audience
- Key sections: Context, Mistakes made, What worked, Takeaways

## Quality Guidelines

**ALWAYS:**
- Start with a hook that creates curiosity
- Explain the "why" before the "how"
- Show real code, not pseudocode
- Include at least one "I struggled with..." moment (humanizes)
- End with actionable takeaways
- Keep code snippets focused (< 30 lines each)
- Write for developers 1-2 years less experienced than you

**NEVER:**
- Start with "In this post, I will..."
- Include every line of code (link to repo instead)
- Skip the problem statement
- Be purely promotional without teaching
- Include sensitive data (keys, internal URLs, customer info)
- Use jargon without explanation
- Make it longer than 10-minute read (2000 words max)

## Tone Examples

**Good opening:**
> Last week, our API started timing out under load. After three failed attempts and one 2 AM debugging session, I finally found the culprit: a sneaky N+1 query hiding in plain sight.

**Bad opening:**
> In this blog post, I will discuss how I optimized our API performance by fixing an N+1 query problem in our database layer.

**Good code explanation:**
> The key insight is caching the user lookup. Instead of hitting the database for each item, we batch the IDs and fetch them all at once:

**Bad code explanation:**
> Below is the code I wrote. It takes the user IDs and puts them in a set, then queries the database.

## Platform-Specific Tips

### Dev.to
- Use `{% tag %}` for embeds
- Add cover image
- Use 3-5 tags
- Include series tag if part of series

### Medium
- Use pull quotes for key insights
- Add images/diagrams
- Keep paragraphs short (3-4 sentences)

### Personal Blog
- Add related posts section
- Include newsletter CTA
- Add social sharing meta tags

## Output Location

**Save drafts to:** `drafts/blog/YYYY-MM-DD_<topic-slug>.md`

Create directory if needed:
```bash
mkdir -p drafts/blog
```

## Important Notes

- **Draft first, polish later** - Get the structure right before wordsmithing
- **One main point per post** - Don't try to cover everything
- **Code is supporting evidence** - The explanation is the star
- **Challenges are gold** - Readers learn most from your mistakes
- **Link, don't paste** - For long code, link to GitHub instead
- **Test your code snippets** - They should work if copy-pasted
- **Schedule time to edit** - First draft is never final
