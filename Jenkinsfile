// EPIConnect — CI/CD pipeline (Jenkins on the same Azure VM)
// Triggered by a GitHub webhook on every push to main.
// See docs/CICD.md for the full description of each stage.
pipeline {
    agent any

    options {
        disableConcurrentBuilds()          // never run two deploys at once
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        PROJECT_DIR = '/var/www/EPIConnect'
        VENV_DIR    = '/var/www/EPIConnect/venv'
        APP_HOST    = 'epiconnect.swedencentral.cloudapp.azure.com'
    }

    stages {

        stage('1. Update Code') {
            steps {
                echo 'Syncing workspace to project directory...'
                // rsync instead of cp: removes deleted files, never touches
                // .env / venv / media, and does not try to preserve ownership
                // (this was the cause of the Jenkins file-ownership conflicts).
                sh '''
                    rsync -rlt --delete --no-owner --no-group --chmod=Dug=rwx,Do=rx,Fug=rw,Fo=r \
                        --exclude '.git/' \
                        --exclude '.env' \
                        --exclude 'venv/' \
                        --exclude 'media/' \
                        --exclude 'staticfiles/' \
                        --exclude 'reports/' \
                        "$WORKSPACE/" "$PROJECT_DIR/"
                '''
            }
        }

        stage('2. Install Dependencies') {
            steps {
                dir("${PROJECT_DIR}") {
                    sh '${VENV_DIR}/bin/pip install --quiet --upgrade pip'
                    sh '${VENV_DIR}/bin/pip install --quiet -r requirements-dev.txt'
                }
            }
        }

        stage('3. Security Scan') {
            steps {
                dir("${PROJECT_DIR}") {
                    sh 'mkdir -p reports'
                    // SAST — fails the build on any medium/high severity issue
                    sh '''
                        ${VENV_DIR}/bin/bandit -r . \
                            -x ./venv,./staticfiles,./media,./reports \
                            --severity-level medium \
                            -f txt -o reports/bandit-report.txt || { cat reports/bandit-report.txt; exit 1; }
                        tail -n 25 reports/bandit-report.txt
                    '''
                    // SCA — fails the build if a runtime dependency has a known CVE
                    sh '${VENV_DIR}/bin/pip-audit -r requirements.txt --format json -o reports/pip-audit-report.json'
                    sh '${VENV_DIR}/bin/pip-audit -r requirements.txt'
                }
            }
            post {
                always {
                    sh 'cp -r ${PROJECT_DIR}/reports "$WORKSPACE/" || true'
                    archiveArtifacts artifacts: 'reports/*', allowEmptyArchive: true
                }
            }
        }

        stage('4. Check & Test') {
            steps {
                dir("${PROJECT_DIR}") {
                    sh '${VENV_DIR}/bin/python manage.py check --deploy --fail-level WARNING'
                    sh '${VENV_DIR}/bin/python manage.py makemigrations --check --dry-run'
                    // Tests run on a throw-away SQLite DB, never on production data
                    sh 'DATABASE_URL= ${VENV_DIR}/bin/python manage.py test --noinput -v 1'
                }
            }
        }

        stage('5. Run Migrations') {
            steps {
                dir("${PROJECT_DIR}") {
                    sh '${VENV_DIR}/bin/python manage.py migrate --noinput'
                }
            }
        }

        stage('6. Collect Static Files') {
            steps {
                dir("${PROJECT_DIR}") {
                    sh '${VENV_DIR}/bin/python manage.py collectstatic --noinput'
                }
            }
        }

        stage('7. Restart & Verify') {
            steps {
                sh 'sudo /bin/systemctl restart gunicorn'
                // Poll the health endpoint (app + DB) instead of a fixed sleep
                sh '''
                    for i in $(seq 1 10); do
                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $APP_HOST" http://127.0.0.1:8000/healthz/ || true)
                        echo "Attempt $i: /healthz/ -> HTTP $STATUS"
                        [ "$STATUS" = "200" ] && { echo "Deployment verified."; exit 0; }
                        sleep 3
                    done
                    echo "Deployment FAILED — /healthz/ never returned 200"
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'Deployment successful! EPIConnect is live.'
        }
        failure {
            echo 'Deployment FAILED. Check logs above.'
            sh 'sudo /bin/systemctl status gunicorn --no-pager || true'
            sh 'sudo /bin/journalctl -u gunicorn -n 50 --no-pager || true'
        }
    }
}
