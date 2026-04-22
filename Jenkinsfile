pipeline {
    agent any

    environment {
        PROJECT_DIR = '/var/www/EPIConnect'
        VENV_DIR    = '/var/www/EPIConnect/venv'
    }

    stages {

        stage('Pull Latest Code') {
            steps {
                echo 'Pulling latest code from GitHub...'
                dir("${PROJECT_DIR}") {
                    sh 'git fetch origin main'
                    sh 'git reset --hard origin/main'
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing Python dependencies...'
                dir("${PROJECT_DIR}") {
                    sh '${VENV_DIR}/bin/pip install -r requirements.txt --quiet'
                }
            }
        }

        stage('Django System Check') {
            steps {
                echo 'Running Django system checks...'
                dir("${PROJECT_DIR}") {
                    sh '${VENV_DIR}/bin/python manage.py check'
                }
            }
        }

        stage('Run Migrations') {
            steps {
                echo 'Applying database migrations...'
                dir("${PROJECT_DIR}") {
                    sh '${VENV_DIR}/bin/python manage.py migrate --noinput'
                }
            }
        }

        stage('Collect Static Files') {
            steps {
                echo 'Collecting static files...'
                dir("${PROJECT_DIR}") {
                    sh '${VENV_DIR}/bin/python manage.py collectstatic --noinput'
                }
            }
        }

        stage('Restart Gunicorn') {
            steps {
                echo 'Restarting Gunicorn service...'
                sh 'sudo /bin/systemctl restart gunicorn'
            }
        }

        stage('Verify Deployment') {
            steps {
                echo 'Verifying deployment...'
                sh 'sleep 5'
                sh '''
                    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
                      -H "Host: epiconnect.swedencentral.cloudapp.azure.com" \
                      http://localhost)
                    echo "HTTP Status: $STATUS"
                    if [ "$STATUS" != "200" ] && [ "$STATUS" != "302" ] && [ "$STATUS" != "301" ]; then
                        echo "Deployment FAILED — HTTP $STATUS"
                        exit 1
                    fi
                    echo "Deployment verified successfully!"
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
            sh 'sudo /bin/systemctl status gunicorn || true'
        }
        always {
            echo 'Pipeline finished.'
        }
    }
}
