# Publishing V138 and connecting it to the competition

The release folder is an isolated Git repository, prepared without research history or credentials. Its code and notebook are frozen V138. Publish this folder, not the parent workspace.

## GitHub CLI

In PowerShell, change directory to this repository. Confirm `gh` is signed into Yoder23:

```powershell
gh auth status
```

If authentication is required, use `gh auth login --hostname github.com --git-protocol https --web` and complete the browser flow. Do not paste access tokens into chat.

With a new, unused repository name:

```powershell
gh repo create Yoder23/arc3-v138 --public --source . --remote origin --push
git push origin v138
gh release create v138 submission/submission.ipynb docs/report/ARC3-Research-and-Submission-Report-V138.pdf --repo Yoder23/arc3-v138 --verify-tag --title "V138: retained learning and bounded planning" --notes-file docs/RELEASE_NOTES.md
```

These commands publish the code and report publicly. If a repository with this name already exists, stop and inspect its contents; do not force-push or replace another project. MIT-0 is already present; do not add GitHub's default MIT template over it.

## GitHub Desktop alternative

Use File > Add local repository and select this `arc3-v138` folder. Choose Publish repository, use the Yoder23 account and repository name `arc3-v138`, and **clear Keep this code private**. Publish. On GitHub, use Releases > Draft a new release; choose tag `v138` (or create it at `main` if absent), paste `docs/RELEASE_NOTES.md`, attach the notebook and report PDF, and click Publish release.

## Verify the public release

Open the repository in a signed-out/private browser window. Confirm the README, LICENSE, readable files under `src/`, compact notebook, and report are accessible. Confirm a published `v138` release exists, and that its assets match the hashes in `RELEASE-MANIFEST.json`. The root license is MIT-0; third-party notices are separately preserved.

## Connect the release to Kaggle

Keep the scored notebook version unchanged. Submit the previously completed compact V138 version with `submission.parquet`. Put the public GitHub release URL in the submission description if that field is still editable. After Kaggle accepts it, retain the submission ID and exact saved version number; add these to repository documentation in a later commit without changing the `v138` tag. Use any official organizer-requested code-release field or form as directed by the competition rules.

Do not spend another daily scored submission just to attach documentation. The 15-page report is a detailed companion; a separate Paper Track entry has its own format and submission requirements. GitHub publication does not enter that track or automatically certify competition eligibility.

Official references: [GitHub CLI repository creation](https://cli.github.com/manual/gh_repo_create), [GitHub Desktop publishing](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop), [GitHub releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository), [ARC Prize rules](https://arcprize.org/competitions/2026), [ARC submission workflow](https://docs.arcprize.org/arc-prize-2026).
