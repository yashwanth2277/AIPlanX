import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react'

export function DataTable({ children }: { children: ReactNode }) {
  return (
    <div className="ax-table-wrap">
      <table className="ax-table">{children}</table>
    </div>
  )
}

export function Th(props: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th {...props} />
}

export function Td(props: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td {...props} />
}

export function Tr({ selected = false, ...props }: HTMLAttributes<HTMLTableRowElement> & { selected?: boolean }) {
  return <tr {...props} className={selected ? 'is-selected' : undefined} />
}
