import { ContactRequestsTable } from "@/widgets/admin/ui/ContactRequestsTable";
import { GenerationJobsTable } from "@/widgets/admin/ui/GenerationJobsTable";
import { SettingsManager } from "@/widgets/admin/ui/SettingsManager";

export default function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <SettingsManager />
      <ContactRequestsTable />
      <GenerationJobsTable />
    </div>
  );
}

