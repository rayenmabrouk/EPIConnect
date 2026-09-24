"""Create the first superuser without putting its password in the task definition.

Run as a one-off ECS task. The password is read at run time from the
application secret in AWS Secrets Manager (key ADMIN_PASSWORD), so it never
appears in environment variables of the web containers, in the ECS API, or in
the pipeline logs. Locally, --password-env lets you pass it via an env var.
"""
import json
import os

from django.core.management.base import BaseCommand, CommandError

from users.models import User


class Command(BaseCommand):
    help = 'Create the initial superuser (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--email', default='admin@epiconnect.local')
        parser.add_argument('--password-env', help='Read the password from this environment variable')

    def handle(self, *args, **opts):
        if User.objects.filter(username=opts['username']).exists():
            self.stdout.write(f"Superuser '{opts['username']}' already exists; nothing to do.")
            return

        if opts['password_env']:
            password = os.environ.get(opts['password_env'])
        else:
            secret_arn = os.environ.get('APP_SECRET_ARN')
            if not secret_arn:
                raise CommandError('APP_SECRET_ARN is not set (or use --password-env).')
            import boto3
            client = boto3.client('secretsmanager')
            payload = json.loads(client.get_secret_value(SecretId=secret_arn)['SecretString'])
            password = payload.get('ADMIN_PASSWORD')

        if not password:
            raise CommandError('No admin password available.')

        User.objects.create_superuser(opts['username'], opts['email'], password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{opts['username']}' created."))
