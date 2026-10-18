# SIMS tests on physical phones

[Run history and manual run button](https://github.com/NousVolition/Nous-Volition/actions/workflows/sims-real-devices.yml)

The **SIMS real phones** workflow builds the commit being checked, then uses BrowserStack Local to serve it to a physical **iPhone 16 / iOS 18.5 / Safari** and **Samsung Galaxy S23 / Android 13 / Chrome**. Both device jobs must pass. The phones verify a revision marker served with the page, so a passing test cannot silently refer to an older live deployment.

## Automatic triggers

- Pushes to `main` changing anything under `studies/sims-evidence-lab/` or the workflow.
- Pull requests changing those paths. Physical tests run for branches in this repository. Fork PRs run the source checks without receiving BrowserStack secrets.
- Manual **Run workflow**, with `build` (default) or `live` to check the published website.

New runs cancel older runs for the same branch or pull request. The workflow uses a two-phone matrix, a 20-minute limit per device test, a 25-minute job limit, and separate tunnel identifiers. Scripts close sessions on completion or interruption; the workflow stops the tunnels even after failure. Idle sessions also expire after 120 seconds.

## Credentials and allowance

Add these **repository Actions secrets** through GitHub Settings → Secrets and variables → Actions:

- `BROWSERSTACK_USERNAME`
- `BROWSERSTACK_ACCESS_KEY`

Use the automation credentials from your BrowserStack account. Do not put them in code, command history, screenshots, or committed files. The workflow fails with a clear missing-secret message until these are configured. A connected BrowserStack MCP account alone does not authenticate a GitHub-hosted runner.

Runs consume the account's BrowserStack Automate minutes. They require available real-device access and parallel capacity. This workflow does not purchase or upgrade a plan; exhausted allowance or unavailable devices cause a visible failure.

## Coverage and evidence

All six page routes receive first-navigation readiness and viewport-fit checks. The four distinct models receive representative selections for every select control, checkbox changes, seed editing with native keyboards, New trial, stage navigation, slider thumb dragging, step/play/pause/finish where present, participant inspection, disclosures, tooltip taps, and vertical/horizontal swipes. All seven navigation links are followed, including Methods and Source on GitHub. Network is checked in landscape and returned to portrait.

Buttons and gestures use Appium W3C touch actions. Select options use WebDriver selection. iPhone seed input uses a native text field and Done; Android uses native key events. Assertions read the resulting state. JavaScript also scrolls controls into view and installs touch/error listeners; it does not synthesize input events. Runtime-error listeners begin after readiness, while startup is checked separately. This is representative coverage, not every possible setting combination or phone/OS version.

Every run saves JSON, JUnit, page screenshots, failure screenshots, and a summary in the GitHub artifact for each device (14-day retention). The summary links to BrowserStack's recording and session log. A failed assertion exits nonzero; earlier failures are never relabeled as passes. Credentials and signed video URLs are excluded from artifacts.

The [October 17 live-device audit](baseline-2026-10-17/report.html) is preserved with its original raw results and explicit passing retests. That historical report is separate from each new CI run.

## Run locally

Node 24 and Python 3 are sufficient for the test code; no npm packages are required. From `web/`:

```sh
python3 build.py
node tests/startup.cjs
node tests/mobile.cjs
node --test tests/real-device/*.test.mjs
```

With credentials supplied securely through the environment, set `SIMS_DEVICE=iphone` or `android`. Set `SIMS_TARGET=live` and run `node tests/real-device/run.mjs` to check the published site. For the built source, start the official BrowserStack Local tunnel, set its `BROWSERSTACK_LOCAL_IDENTIFIER`, use `SIMS_TARGET=build`, and run the same script. The script serves only the six built pages from `dist/` on loopback port 8000. The phone connects through `http://bs-local.com:8000/`.

Automatic runs build `web/src/` with `web/build.py`, which is the portable source for the published site. Editing the historical `fragments/` or `site/` exports also triggers a run, but changes to those copies must be incorporated into `web/src/` to change the browser application under test.

## Maintenance

Device names and OS versions are explicit in `session.mjs`. Update them deliberately if BrowserStack retires an OS. The iPhone 16 portrait offset is 59 points; landscape offsets are calibrated from a trusted touch event. Changing the iPhone model requires rechecking that calibration and the native keyboard selectors. GitHub Actions dependencies are pinned to reviewed commit SHAs.

Official references: [BrowserStack Local action](https://github.com/browserstack/github-actions/tree/master/setup-local), [real-device capabilities](https://www.browserstack.com/docs/automate/capabilities), [native Android keys](https://appium.github.io/appium.io/docs/en/commands/device/keys/press-keycode/), [GitHub encrypted secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).
