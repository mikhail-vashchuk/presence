from django.db import migrations, models


def move_name_to_human(apps, schema_editor):
    Human = apps.get_model("humans", "Human")

    for human in Human.objects.select_related("user"):
        human.first_name = human.user.first_name
        human.last_name = human.user.last_name

        human.save(
            update_fields=[
                "first_name",
                "last_name",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("humans", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="human",
            name="first_name",
            field=models.CharField(
                max_length=150,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="human",
            name="last_name",
            field=models.CharField(
                max_length=150,
                null=True,
            ),
        ),
        migrations.RunPython(
            move_name_to_human,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="human",
            name="first_name",
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name="human",
            name="last_name",
            field=models.CharField(max_length=150),
        ),
    ]