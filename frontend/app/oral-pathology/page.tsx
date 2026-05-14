import Link from "next/link";
import {
  ArrowRight,
  ClipboardCheck,
  ClipboardList,
  FileText,
  FolderKanban,
  HeartPulse,
  Microscope,
  Route,
  ShieldCheck,
  Stethoscope,
  UploadCloud,
} from "lucide-react";
import styles from "./OralPathology.module.css";

const patientActions = [
  {
    icon: UploadCloud,
    title: "Submit a concern",
    text: "Share symptoms, lesion history, images, and relevant documents in one guided intake.",
  },
  {
    icon: ClipboardCheck,
    title: "View case status",
    text: "Follow review progress, requested updates, and specialist routing decisions.",
  },
  {
    icon: HeartPulse,
    title: "Read clinical guidance",
    text: "Receive plain-language next steps while the clinical team reviews the case.",
  },
];

const assistantActions = [
  {
    icon: FolderKanban,
    title: "Organize pathology cases",
    text: "Sort submissions by acuity, completeness, lesion type, and required follow-up.",
  },
  {
    icon: FileText,
    title: "Prepare triage summaries",
    text: "Create structured notes for specialist review with history, images, and risk flags.",
  },
  {
    icon: Route,
    title: "Route to specialists",
    text: "Assign cases to oral medicine, pathology, surgery, or urgent clinical review.",
  },
];

export default function OralPathologyPage() {
  return (
    <div className={styles.page}>
      <section className={styles.hero} aria-labelledby="oral-pathology-title">
        <div className={styles.heroCopy}>
          <div className={styles.eyebrow}>
            <Microscope size={18} aria-hidden="true" />
            Oral pathology module
          </div>
          <h1 id="oral-pathology-title">Oral Pathology Workspace</h1>
          <p>
            A role-based interface for patients and clinical assistants to
            manage oral pathology cases with clarity and confidence.
          </p>
        </div>

        <div className={styles.heroVisual} aria-hidden="true">
          <div className={styles.specimenCard}>
            <div className={styles.specimenHeader}>
              <span>Case readiness</span>
              <ShieldCheck size={18} />
            </div>
            <div className={styles.specimenGrid}>
              <span />
              <span />
              <span />
              <span />
            </div>
          </div>
          <div className={styles.pulseLine}>
            <span />
            <span />
            <span />
          </div>
        </div>
      </section>

      <section className={styles.roleGrid} aria-label="Role work areas">
        <article className={`${styles.rolePanel} ${styles.patientPanel}`}>
          <div className={styles.panelTopline} />
          <div className={styles.panelHeader}>
            <div className={styles.roleIcon}>
              <Stethoscope size={28} aria-hidden="true" />
            </div>
            <div>
              <p className={styles.roleKicker}>Patient</p>
              <h2>Start and follow your pathology case</h2>
            </div>
          </div>
          <p className={styles.panelIntro}>
            Submit oral concerns securely, add supporting lesion photos or
            documents, and stay informed as your case moves through review.
          </p>

          <div className={styles.actionList}>
            {patientActions.map((action) => {
              const Icon = action.icon;
              return (
                <div className={styles.actionItem} key={action.title}>
                  <div className={styles.actionIcon}>
                    <Icon size={20} aria-hidden="true" />
                  </div>
                  <div>
                    <h3>{action.title}</h3>
                    <p>{action.text}</p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className={styles.panelFooter}>
            <Link href="/oral-pathology/new" className={styles.primaryButton}>
              New submission
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
            <Link href="/oral-pathology/status" className={styles.secondaryLink}>
              Check case status
            </Link>
          </div>
        </article>

        <article className={`${styles.rolePanel} ${styles.assistantPanel}`}>
          <div className={styles.panelTopline} />
          <div className={styles.panelHeader}>
            <div className={styles.roleIcon}>
              <ClipboardList size={28} aria-hidden="true" />
            </div>
            <div>
              <p className={styles.roleKicker}>Assistant</p>
              <h2>Review, triage, and route submissions</h2>
            </div>
          </div>
          <p className={styles.panelIntro}>
            Work through incoming cases with structured notes, image review,
            triage summaries, and specialist routing controls.
          </p>

          <div className={styles.actionList}>
            {assistantActions.map((action) => {
              const Icon = action.icon;
              return (
                <div className={styles.actionItem} key={action.title}>
                  <div className={styles.actionIcon}>
                    <Icon size={20} aria-hidden="true" />
                  </div>
                  <div>
                    <h3>{action.title}</h3>
                    <p>{action.text}</p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className={styles.panelFooter}>
            <Link href="/oral-pathology/review" className={styles.primaryButton}>
              Review queue
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
            <Link href="/oral-pathology/triage" className={styles.secondaryLink}>
              Draft triage summary
            </Link>
          </div>
        </article>
      </section>

      <section className={styles.guidanceBand} aria-label="Clinical workflow">
        <div>
          <span>Clinical workflow</span>
          <strong>Intake, review, triage, and specialist routing stay separated by role.</strong>
        </div>
        <p>
          The workspace keeps patient-facing guidance clear while giving
          assistants the operational tools needed to prepare complete oral
          pathology referrals.
        </p>
      </section>
    </div>
  );
}
