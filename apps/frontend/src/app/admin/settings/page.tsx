import { ContactRequestsTable } from "@/widgets/admin/ui/ContactRequestsTable";
import { GenerationJobsControlPanel } from "@/widgets/admin/ui/GenerationJobsControlPanel";
import { SettingsManager } from "@/widgets/admin/ui/SettingsManager";

export default function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <SettingsManager />
      <ContactRequestsTable />
      <GenerationJobsControlPanel />
    </div>
  );
}
