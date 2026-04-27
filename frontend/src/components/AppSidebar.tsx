import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  FolderKanban,
  Receipt,
  Wallet,
  FileUp,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

type NavItem = {
  title: string;
  url: string;
  icon: typeof LayoutDashboard;
  exact?: boolean;
};

const items: NavItem[] = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard, exact: true },
  { title: "Projects", url: "/projects", icon: FolderKanban },
  { title: "Expenses", url: "/expenses", icon: Receipt },
  { title: "Income", url: "/income", icon: Wallet },
  { title: "PDF Import", url: "/pdf-import", icon: FileUp },
];

export function AppSidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const isActive = (url: string, exact?: boolean) =>
    exact ? pathname === url : pathname === url || pathname.startsWith(url + "/");

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b">
        <div className="flex items-center gap-2 px-2 py-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold">
            ₹
          </div>
          <div className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">Expense Tracker</span>
            <span className="text-xs text-muted-foreground">MYR · Projects</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => {
                const active = isActive(item.url, item.exact);
                return (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton asChild isActive={active}>
                      <Link to={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
