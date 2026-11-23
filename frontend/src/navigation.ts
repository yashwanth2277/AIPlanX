export type PageMeta = {
  title: string
  description: string
}

export function pageMeta(pathname: string): PageMeta {
  if (pathname === '/' || pathname === '/projects') {
    return {
      title: 'Projects',
      description: 'Open a saved plan or start a planning job. Projects stay on this page after they are created.',
    }
  }
  if (pathname === '/team') {
    return {
      title: 'Team Management',
      description: 'People currently available to the planning and scheduling engine.',
    }
  }
  if (pathname === '/notifications') {
    return {
      title: 'Notifications',
      description: 'Workspace alerts will appear here when a notification service is available.',
    }
  }
  if (pathname === '/settings') {
    return {
      title: 'Settings',
      description: 'Appearance for this browser and the live API connection.',
    }
  }
  if (pathname === '/profile') {
    return {
      title: 'Profile',
      description: 'This workspace does not have signed-in accounts yet.',
    }
  }
  if (pathname.endsWith('/overview')) {
    return {
      title: 'Overview',
      description: 'Status, progress, and priority work for the open project.',
    }
  }
  if (pathname.endsWith('/studio')) {
    return {
      title: 'AI Planning Studio',
      description: 'Generate a plan. The job stores a new project and can open a management session.',
    }
  }
  if (pathname.endsWith('/team')) {
    return {
      title: 'Team',
      description: 'Assignments and the weekly schedule for this session.',
    }
  }
  if (pathname.endsWith('/tasks')) {
    return {
      title: 'Tasks & Assignments',
      description: 'Update progress, record delays, and reassign work.',
    }
  }
  if (pathname.endsWith('/timeline')) {
    return {
      title: 'Progress & Timeline',
      description: 'Planned and actual progress, with the scheduled weeks for this session.',
    }
  }
  if (pathname.endsWith('/reports')) {
    return {
      title: 'Reports & Analysis',
      description: 'Management report, recorded delays, and planning risks.',
    }
  }
  if (pathname.endsWith('/assistant')) {
    return {
      title: 'AI Assistant',
      description: 'Answers use the current session and do not change saved project state.',
    }
  }
  if (pathname.endsWith('/activity')) {
    return {
      title: 'Activity History',
      description: 'Task updates recorded for this session.',
    }
  }
  return {
    title: 'Page not found',
    description: 'That address is not part of AIPlanX.',
  }
}

export function workspaceBase(pathname: string): string | null {
  const project = pathname.match(/^\/projects\/(\d+)(?:\/|$)/)
  if (project) return `/projects/${project[1]}`
  const session = pathname.match(/^\/sessions\/([^/]+)(?:\/|$)/)
  if (session) return `/sessions/${session[1]}`
  return null
}
