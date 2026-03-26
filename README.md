# chriswjohnston-stage

Preview site for chriswjohnston.ca campaign site.
Lives at stage.chriswjohnston.ca — always shows campaign mode.

## How to use

1. Edit src/campaign/index.html
2. Commit and push to main
3. Build runs automatically — preview at stage.chriswjohnston.ca
4. When happy: Actions → Promote to Production → Run workflow → type PROMOTE

## GitHub Secrets needed

- PROD_TOKEN — Personal Access Token with repo scope on chriswjohnston-site
  (same token as REPO_TOKEN, just named differently here)

## Setup

1. Create repo: chriswjohnston-stage
2. Upload all these files
3. Settings → Pages → main branch → /docs folder
4. Add PROD_TOKEN secret
5. In cPanel: CNAME record stage → chriswjohnston.github.io
