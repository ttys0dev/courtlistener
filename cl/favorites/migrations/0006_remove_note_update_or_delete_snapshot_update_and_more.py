# Generated by Django 4.2 on 2023-05-01 05:23

from django.db import migrations
import pgtrigger.compiler
import pgtrigger.migrations


class Migration(migrations.Migration):

    dependencies = [
        ("favorites", "0005_update_triggers"),
    ]

    operations = [
        pgtrigger.migrations.RemoveTrigger(
            model_name="note",
            name="update_or_delete_snapshot_update",
        ),
        pgtrigger.migrations.RemoveTrigger(
            model_name="usertag",
            name="update_or_delete_snapshot_update",
        ),
        pgtrigger.migrations.AddTrigger(
            model_name="note",
            trigger=pgtrigger.compiler.Trigger(
                name="update_or_delete_snapshot_update",
                sql=pgtrigger.compiler.UpsertTriggerSql(
                    condition='WHEN (OLD."id" IS DISTINCT FROM (NEW."id") OR OLD."date_created" IS DISTINCT FROM (NEW."date_created") OR OLD."user_id" IS DISTINCT FROM (NEW."user_id") OR OLD."cluster_id_id" IS DISTINCT FROM (NEW."cluster_id_id") OR OLD."audio_id_id" IS DISTINCT FROM (NEW."audio_id_id") OR OLD."docket_id_id" IS DISTINCT FROM (NEW."docket_id_id") OR OLD."recap_doc_id_id" IS DISTINCT FROM (NEW."recap_doc_id_id") OR OLD."name" IS DISTINCT FROM (NEW."name") OR OLD."notes" IS DISTINCT FROM (NEW."notes"))',
                    func='INSERT INTO "favorites_noteevent" ("audio_id_id", "cluster_id_id", "date_created", "date_modified", "docket_id_id", "id", "name", "notes", "pgh_context_id", "pgh_created_at", "pgh_label", "pgh_obj_id", "recap_doc_id_id", "user_id") VALUES (OLD."audio_id_id", OLD."cluster_id_id", OLD."date_created", OLD."date_modified", OLD."docket_id_id", OLD."id", OLD."name", OLD."notes", _pgh_attach_context(), NOW(), \'update_or_delete_snapshot\', OLD."id", OLD."recap_doc_id_id", OLD."user_id"); RETURN NULL;',
                    hash="9731e3216c6d227dcc5c11083309a6318e0f9499",
                    operation="UPDATE",
                    pgid="pgtrigger_update_or_delete_snapshot_update_ed3a1",
                    table="favorites_note",
                    when="AFTER",
                ),
            ),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name="usertag",
            trigger=pgtrigger.compiler.Trigger(
                name="update_or_delete_snapshot_update",
                sql=pgtrigger.compiler.UpsertTriggerSql(
                    condition='WHEN (OLD."id" IS DISTINCT FROM (NEW."id") OR OLD."date_created" IS DISTINCT FROM (NEW."date_created") OR OLD."user_id" IS DISTINCT FROM (NEW."user_id") OR OLD."name" IS DISTINCT FROM (NEW."name") OR OLD."title" IS DISTINCT FROM (NEW."title") OR OLD."description" IS DISTINCT FROM (NEW."description") OR OLD."published" IS DISTINCT FROM (NEW."published"))',
                    func='INSERT INTO "favorites_usertagevent" ("date_created", "date_modified", "description", "id", "name", "pgh_context_id", "pgh_created_at", "pgh_label", "pgh_obj_id", "published", "title", "user_id") VALUES (OLD."date_created", OLD."date_modified", OLD."description", OLD."id", OLD."name", _pgh_attach_context(), NOW(), \'update_or_delete_snapshot\', OLD."id", OLD."published", OLD."title", OLD."user_id"); RETURN NULL;',
                    hash="680021ed57671af8d431e0fcc2fa28af576df12e",
                    operation="UPDATE",
                    pgid="pgtrigger_update_or_delete_snapshot_update_9deec",
                    table="favorites_usertag",
                    when="AFTER",
                ),
            ),
        ),
    ]
