BEGIN;
--
-- Create model NeonWebhookEvents
--
CREATE TABLE "donate_neonwebhookevents" ("id" integer NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "trigger" smallint NULL CHECK ("trigger" >= 0), "account_id" varchar NOT NULL, "membership_id" varchar NOT NULL, "content" jsonb NULL);
--
-- Create model NeonMembership
--
CREATE TABLE "donate_neonmembership" ("id" integer NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "neon_id" varchar NOT NULL, "level" smallint NULL CHECK ("level" >= 0), "termination_date" timestamp with time zone NULL, "user_id" integer NOT NULL UNIQUE);

ALTER TABLE "donate_neonmembership" ADD CONSTRAINT "donate_neonmembership_user_id_c598b2fa_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED;

COMMIT;
