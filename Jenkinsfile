pipeline {
  agent any

  options {
    disableConcurrentBuilds()
    timeout(time: 20, unit: 'MINUTES')
    timestamps()
  }

  environment {
    PROJECT_PREFIX = 'mealorder'
    PREVIEW_LIMIT  = '3'
    DEPLOY_PATH    = '/home/nol/Corporate-Meal-Ordering-System'
    PUBLIC_BASE    = 'https://nol.cs.nycu.edu.tw'
  }

  stages {

    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Deploy main') {
      when { branch 'main' }
      steps {
        sh '''
          set -euo pipefail
          cd "$DEPLOY_PATH"
          git fetch --all --prune
          git checkout main
          git reset --hard origin/main
          docker compose -p mealorder-main build
          docker compose -p mealorder-main up -d
        '''
      }
    }

    stage('Deploy preview') {
      when { expression { return env.CHANGE_ID != null } }
      environment {
        BRANCH_RAW = "${env.CHANGE_BRANCH}"
      }
      steps {
        withCredentials([string(credentialsId: 'gh-pat', variable: 'GH_TOKEN')]) {
          sh '''
            set -euo pipefail

            if [ -z "${BRANCH_RAW:-}" ]; then
              echo "BRANCH_RAW empty; refusing to deploy" >&2
              exit 2
            fi

            SLUG=$(bash scripts/preview-sanitize-branch.sh "$BRANCH_RAW")
            if [ -z "$SLUG" ]; then
              gh pr comment "$CHANGE_ID" --body "Preview deploy aborted: branch name '$BRANCH_RAW' produces empty slug."
              echo "empty SLUG from sanitize" >&2
              exit 2
            fi

            PROJECT="${PROJECT_PREFIX}-${SLUG}"
            ROOT_PATH="/preview/${SLUG}"

            COUNT=$(docker compose ls --filter name=${PROJECT_PREFIX}- --format json \
              | jq '[.[] | select(.Name != "'"$PROJECT"'" and .Name != "'"${PROJECT_PREFIX}"'-main")] | length')
            if [ "$COUNT" -ge "$PREVIEW_LIMIT" ]; then
              gh pr comment "$CHANGE_ID" --body "Preview slot full ($COUNT/$PREVIEW_LIMIT). Will retry on next push."
              echo "preview slot full" >&2
              exit 1
            fi

            BRANCH_RAW="$BRANCH_RAW" ROOT_PATH="$ROOT_PATH" SLUG="$SLUG" docker compose \
              -p "$PROJECT" \
              -f docker-compose.yml \
              -f infra/preview/docker-compose.preview.yml \
              up -d --build

            URL="${PUBLIC_BASE}/preview/${SLUG}/"
            gh pr comment "$CHANGE_ID" --body "Preview: ${URL} (health: ${URL}health)"
          '''
        }
      }
    }
  }

  post {
    always { cleanWs() }
  }
}
