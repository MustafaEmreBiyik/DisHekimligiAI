"""S11-T01: Recommendation v2 schema (IRT + BKT + XGB registry + feature log).

Adds four tables that back the v2 hybrid recommendation engine:

    * irt_parameters              — per-question IRT (a, b, optional c)
    * mastery_states              — per (user, topic) BKT posterior
    * recommendation_model_versions — XGB ranker artefact registry
    * recommendation_feature_logs — per-recommendation feature/SHAP snapshot

Migration is idempotent (mirrors the n9i3l1m48h65 pattern) so re-application
on a partially-migrated dev DB is safe.

Revision ID: o0j4m2n59i76
Revises: n9i3l1m48h65
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


revision = "o0j4m2n59i76"
down_revision = "n9i3l1m48h65"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "irt_parameters"):
        op.create_table(
            "irt_parameters",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("model", sa.String(), nullable=False, server_default="2PL"),
            sa.Column("difficulty_b", sa.Float(), nullable=False),
            sa.Column("discrimination_a", sa.Float(), nullable=False),
            sa.Column("guessing_c", sa.Float(), nullable=True),
            sa.Column("sample_size", sa.Integer(), nullable=False),
            sa.Column("fit_log_likelihood", sa.Float(), nullable=True),
            sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("calibrated_at", sa.DateTime(), nullable=False),
            sa.Column("calibration_run_id", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("question_id", name="uq_irt_parameters_question_id"),
        )
        op.create_index("ix_irt_parameters_id", "irt_parameters", ["id"])
        op.create_index("ix_irt_parameters_question_id", "irt_parameters", ["question_id"])
        op.create_index("ix_irt_parameters_is_synthetic", "irt_parameters", ["is_synthetic"])
        op.create_index("ix_irt_parameters_calibrated_at", "irt_parameters", ["calibrated_at"])
        op.create_index("ix_irt_parameters_calibration_run_id", "irt_parameters", ["calibration_run_id"])

    if not _has_table(bind, "mastery_states"):
        op.create_table(
            "mastery_states",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("topic_id", sa.String(), nullable=False),
            sa.Column("mastery_prob", sa.Float(), nullable=False),
            sa.Column("p_init", sa.Float(), nullable=False, server_default="0.20"),
            sa.Column("p_transit", sa.Float(), nullable=False, server_default="0.10"),
            sa.Column("p_slip", sa.Float(), nullable=False, server_default="0.10"),
            sa.Column("p_guess", sa.Float(), nullable=False, server_default="0.20"),
            sa.Column("n_observations", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_observation_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "topic_id", name="uq_mastery_user_topic"),
        )
        op.create_index("ix_mastery_states_id", "mastery_states", ["id"])
        op.create_index("ix_mastery_states_user_id", "mastery_states", ["user_id"])
        op.create_index("ix_mastery_states_topic_id", "mastery_states", ["topic_id"])

    if not _has_table(bind, "recommendation_model_versions"):
        op.create_table(
            "recommendation_model_versions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("algorithm_version", sa.String(), nullable=False),
            sa.Column("model_blob_path", sa.String(), nullable=False),
            sa.Column("trained_at", sa.DateTime(), nullable=False),
            sa.Column("training_sample_size", sa.Integer(), nullable=False),
            sa.Column("ndcg_at_5", sa.Float(), nullable=True),
            sa.Column("hit_rate_at_5", sa.Float(), nullable=True),
            sa.Column("map_at_10", sa.Float(), nullable=True),
            sa.Column("feature_set_hash", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("algorithm_version", name="uq_recommendation_model_versions_algorithm_version"),
        )
        op.create_index("ix_recommendation_model_versions_id", "recommendation_model_versions", ["id"])
        op.create_index(
            "ix_recommendation_model_versions_algorithm_version",
            "recommendation_model_versions",
            ["algorithm_version"],
        )
        op.create_index("ix_recommendation_model_versions_trained_at", "recommendation_model_versions", ["trained_at"])
        op.create_index("ix_recommendation_model_versions_is_active", "recommendation_model_versions", ["is_active"])

    if not _has_table(bind, "recommendation_feature_logs"):
        op.create_table(
            "recommendation_feature_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("snapshot_id", sa.Integer(), nullable=False),
            sa.Column("model_version_id", sa.Integer(), nullable=False),
            sa.Column("feature_vector_json", sa.JSON(), nullable=False),
            sa.Column("shap_values_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["snapshot_id"], ["recommendation_snapshots.id"]),
            sa.ForeignKeyConstraint(["model_version_id"], ["recommendation_model_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_recommendation_feature_logs_id", "recommendation_feature_logs", ["id"])
        op.create_index(
            "ix_recommendation_feature_logs_snapshot_id",
            "recommendation_feature_logs",
            ["snapshot_id"],
        )
        op.create_index(
            "ix_recommendation_feature_logs_model_version_id",
            "recommendation_feature_logs",
            ["model_version_id"],
        )
        op.create_index(
            "ix_recommendation_feature_logs_created_at",
            "recommendation_feature_logs",
            ["created_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "recommendation_feature_logs"):
        op.drop_index("ix_recommendation_feature_logs_created_at", table_name="recommendation_feature_logs")
        op.drop_index("ix_recommendation_feature_logs_model_version_id", table_name="recommendation_feature_logs")
        op.drop_index("ix_recommendation_feature_logs_snapshot_id", table_name="recommendation_feature_logs")
        op.drop_index("ix_recommendation_feature_logs_id", table_name="recommendation_feature_logs")
        op.drop_table("recommendation_feature_logs")

    if _has_table(bind, "recommendation_model_versions"):
        op.drop_index("ix_recommendation_model_versions_is_active", table_name="recommendation_model_versions")
        op.drop_index("ix_recommendation_model_versions_trained_at", table_name="recommendation_model_versions")
        op.drop_index(
            "ix_recommendation_model_versions_algorithm_version",
            table_name="recommendation_model_versions",
        )
        op.drop_index("ix_recommendation_model_versions_id", table_name="recommendation_model_versions")
        op.drop_table("recommendation_model_versions")

    if _has_table(bind, "mastery_states"):
        op.drop_index("ix_mastery_states_topic_id", table_name="mastery_states")
        op.drop_index("ix_mastery_states_user_id", table_name="mastery_states")
        op.drop_index("ix_mastery_states_id", table_name="mastery_states")
        op.drop_table("mastery_states")

    if _has_table(bind, "irt_parameters"):
        op.drop_index("ix_irt_parameters_calibration_run_id", table_name="irt_parameters")
        op.drop_index("ix_irt_parameters_calibrated_at", table_name="irt_parameters")
        op.drop_index("ix_irt_parameters_is_synthetic", table_name="irt_parameters")
        op.drop_index("ix_irt_parameters_question_id", table_name="irt_parameters")
        op.drop_index("ix_irt_parameters_id", table_name="irt_parameters")
        op.drop_table("irt_parameters")
