pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Set up Python') {
            steps {
                sh 'python3 --version'
            }
        }

        stage('Install dependencies') {
            steps {
                sh 'pip3 install -r requirements.txt'
            }
        }

        stage('Run backend tests') {
            steps {
                sh 'pytest backend/tests'
            }
        }

        stage('Build backend image') {
            steps {
                sh 'docker build -f backend/Dockerfile -t meal-ordering-backend:test .'
            }
        }

        stage('Build frontend image') {
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
