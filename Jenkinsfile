pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Run Python Tests (Docker)') {
            steps {
                script {
                    docker.image('python:3.12').inside {
                        sh '''
                        python --version
                        pip install --user -r requirements.txt
			export PATH=$PATH:$HOME/.local/bin
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
            echo 'Build Success ✅'
        }
        failure {
            echo 'Build Failed ❌'
        }
    }
}
