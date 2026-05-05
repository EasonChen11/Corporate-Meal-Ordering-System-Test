pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Run Python Tests') {
            steps {
                script {
                    docker.image('python:3.12').inside {
                        sh '''
                        python --version
                        python -m venv .venv
                        . .venv/bin/activate
                        pip install --upgrade pip
                        pip install -r requirements.txt
                        pytest backend/tests
                        '''
                    }
                }
            }
        }

        stage('Build backend image') {
            when {
                branch 'main'
            }
            steps {
                sh 'docker build -f backend/Dockerfile -t meal-ordering-backend:test .'
            }
        }

        stage('Build frontend image') {
            when {
                branch 'main'
            }
            steps {
                sh 'docker build -t meal-ordering-frontend:test ./frontend'
            }
        }
    }

    post {
        success {
            echo 'Jenkins pipeline success'
        }
        failure {
            echo 'Jenkins pipeline failed'
        }
        always {
            cleanWs()
        }
    }
}
