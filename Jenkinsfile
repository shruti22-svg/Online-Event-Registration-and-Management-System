pipeline {
    agent any

    options {
        timeout(time: 25, unit: 'MINUTES')
    }

    environment {
        IMAGE_NAME = 'event-registration-system'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Selenium tests in Docker') {
            steps {
                sh 'docker compose -f docker-compose.ci.yml up --build --abort-on-container-exit --exit-code-from tests'
            }
        }

        stage('Build Docker image') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest .'
            }
        }
    }

    post {
        always {
            sh 'docker compose -f docker-compose.ci.yml down -v || true'
        }
        success {
            echo 'Pipeline completed successfully.'
        }
        failure {
            echo 'Pipeline failed. Check the stage logs.'
        }
    }
}
