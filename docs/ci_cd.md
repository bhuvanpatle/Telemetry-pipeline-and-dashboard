# CI/CD Pipeline Documentation

This document describes the GitHub Actions workflows used for Continuous Integration and Continuous Deployment in the Telemetry Pipeline and Dashboard project.

## 📊 Workflow Status Badges

[![CI Pipeline](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/ci.yml)
[![Deploy Frontend](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/deploy_frontend.yml/badge.svg)](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/deploy_frontend.yml)
[![Pages Deployment](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/pages.yml/badge.svg)](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/pages.yml)

## 🔄 Available Workflows

### 1. CI Pipeline (`ci.yml`)

**Triggers:**

- Push to `main` branch
- Pull requests to `main` branch

**Jobs:**

- **python-backend-tests**: Tests Python components (simulator, collector, backend, replay)
- **frontend-build-and-tests**: Builds and tests the React frontend
- **ci-summary**: Provides workflow summary and results

**Features:**

- ✅ Python 3.10 testing with pytest
- ✅ Frontend linting with ESLint
- ✅ Code coverage reporting
- ✅ Artifact uploads for test results
- ✅ Comprehensive error reporting

### 2. Frontend Deployment (`deploy_frontend.yml`)

**Triggers:**

- Push to `main` branch (when frontend files change)
- Manual workflow dispatch

**Jobs:**

- **build-frontend**: Creates production build
- **deploy-pages**: Deploys to GitHub Pages
- **deploy-fallback**: Backup deployment method

**Features:**

- ✅ Automatic GitHub Pages deployment
- ✅ Manual deployment option
- ✅ Fallback deployment method
- ✅ Build artifact preservation

### 3. Release Creation (`release.yml`)

**Triggers:**

- Push of semantic version tags (e.g., `v1.0.0`, `v2.1.3`)

**Jobs:**

- **create-release**: Creates GitHub release with assets
- **deploy-release-frontend**: Auto-deploys frontend for stable releases

**Features:**

- ✅ Automatic changelog generation
- ✅ Frontend build packaging
- ✅ Grafana dashboard packaging
- ✅ Python source distribution
- ✅ Release asset uploads

## 🚀 How to Use the Workflows

### Running CI Tests

CI tests run automatically on every push and pull request. To manually check your changes:

```bash
# Run tests locally before pushing
make test

# Or run pytest directly
python -m pytest FAT_tests/ -v

# Check frontend build locally
cd frontend
npm run build
npm run lint  # if available
```

### Manual Frontend Deployment

To manually deploy the frontend to GitHub Pages:

1. **Via GitHub UI:**

   - Go to [Actions → Deploy Frontend](https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions/workflows/deploy_frontend.yml)
   - Click "Run workflow"
   - Select branch `main`
   - Enter deployment reason (optional)
   - Click "Run workflow"

2. **Via GitHub CLI:**
   ```bash
   gh workflow run deploy_frontend.yml -f deploy_reason="Manual deployment for testing"
   ```

### Creating a Release

To create a new release:

1. **Create and push a semantic version tag:**

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **The release workflow will automatically:**
   - Create a GitHub release
   - Generate changelog from commits
   - Build and package all components
   - Upload release assets
   - Deploy frontend (for stable releases)

## 📦 Artifacts and Downloads

### CI Artifacts

After each CI run, you can download:

- **pytest-results**: Test reports and coverage data (30 days retention)
- **frontend-dist**: Production frontend build (30 days retention)

### Release Assets

Each release includes:

- **frontend-{version}.tar.gz**: Production frontend build
- **grafana-dashboards-{version}.tar.gz**: Grafana dashboard definitions
- **python-source-{version}.tar.gz**: Python source distribution

## 🔧 Configuration and Secrets

### Required Secrets

The workflows use the following GitHub secrets:

| Secret          | Usage                          | Required         |
| --------------- | ------------------------------ | ---------------- |
| `GITHUB_TOKEN`  | Automatic GitHub operations    | ✅ Auto-provided |
| `CUSTOM_DOMAIN` | Custom domain for GitHub Pages | ❌ Optional      |

### Environment Variables

Key environment variables used in workflows:

- `PYTHON_VERSION`: Python version for testing (default: 3.10)
- `NODE_VERSION`: Node.js version for frontend (default: 18)
- `VITE_BASE_PATH`: Base path for frontend deployment
- `VITE_APP_VERSION`: Version number for frontend builds

## 🌐 GitHub Pages Setup

### Automatic Setup

1. The workflows automatically configure GitHub Pages
2. Frontend is deployed to: `https://bhuvanpatle.github.io/Telemetry-pipeline-and-dashboard/`
3. Uses the `gh-pages` branch for deployment

### Manual Setup (if needed)

1. Go to repository **Settings → Pages**
2. Set **Source** to "Deploy from a branch"
3. Select **Branch**: `gh-pages`
4. Select **Folder**: `/ (root)`
5. Click **Save**

### Custom Domain Setup

To use a custom domain:

1. Add `CUSTOM_DOMAIN` secret with your domain name
2. Create a `CNAME` file in the frontend build
3. Configure DNS to point to GitHub Pages

## 🔍 Troubleshooting

### Common Issues

**CI Tests Failing:**

```bash
# Check workflow logs in GitHub Actions
# Download pytest-results artifact for detailed reports
# Run tests locally to debug:
python -m pytest FAT_tests/ -v --tb=short
```

**Frontend Build Failing:**

```bash
# Check Node.js version compatibility
# Verify package.json scripts exist
cd frontend
npm ci
npm run build
```

**GitHub Pages Not Updating:**

```bash
# Check deploy_frontend.yml workflow logs
# Verify GitHub Pages is enabled in repository settings
# Try manual deployment workflow dispatch
```

**Release Creation Failing:**

```bash
# Ensure tag follows semantic versioning (v1.0.0)
# Check repository write permissions
# Verify all required files exist (requirements.txt, frontend/package.json)
```

### Debug Commands

**View workflow status:**

```bash
gh run list --workflow=ci.yml
gh run view <run-id>
```

**Download artifacts:**

```bash
gh run download <run-id>
```

**Trigger manual workflows:**

```bash
gh workflow run deploy_frontend.yml
gh workflow run ci.yml
```

## 📊 Monitoring and Alerts

### Workflow Notifications

GitHub automatically sends notifications for:

- ✅ Successful deployments
- ❌ Failed workflow runs
- 📧 Email notifications (if enabled)

### Status Monitoring

Monitor workflow health through:

- Repository **Actions** tab
- Workflow status badges in README
- GitHub mobile app notifications
- Third-party monitoring tools (optional)

## 🔄 Local Testing with Act

To test workflows locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or
choco install act  # Windows

# Test CI workflow
act push

# Test with specific event
act workflow_dispatch -W .github/workflows/deploy_frontend.yml

# Test with secrets
act -s GITHUB_TOKEN=your_token
```

## 📈 Performance Optimization

### Caching Strategy

The workflows use caching for:

- **pip dependencies**: `~/.cache/pip` (keyed by `requirements.txt`)
- **npm dependencies**: `~/.npm` (keyed by `package-lock.json`)
- **Node.js setup**: Built-in caching via `actions/setup-node@v4`

### Workflow Optimization Tips

1. **Use workflow concurrency** to prevent multiple deployments
2. **Cache dependencies** to reduce install time
3. **Fail fast** for quicker feedback
4. **Parallel jobs** where possible
5. **Conditional execution** to skip unnecessary steps

## 🚀 Advanced Usage

### Custom Deployment Environments

To add staging/production environments:

1. Create environment in repository settings
2. Add environment-specific secrets
3. Modify workflows to use environments:

```yaml
environment:
  name: production
  url: ${{ steps.deployment.outputs.page_url }}
```

### Matrix Testing

To test multiple Python/Node versions:

```yaml
strategy:
  matrix:
    python-version: [3.9, 3.10, 3.11]
    node-version: [16, 18, 20]
```

### Integration Testing

Add integration tests with real services:

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:latest
  influxdb:
    image: influxdb:2.0
```

---

**For additional help, check the [GitHub Actions documentation](https://docs.github.com/en/actions) or create an issue in this repository.**
