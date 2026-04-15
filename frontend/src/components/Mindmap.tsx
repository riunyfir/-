import { useEffect, useMemo, useRef } from 'react'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'

const transformer = new Transformer()

export function Mindmap({ markdown }: { markdown: string }) {
  const svgRef = useRef<SVGSVGElement | null>(null)
  const data = useMemo(() => transformer.transform(markdown || '# 空').root, [markdown])

  useEffect(() => {
    if (!svgRef.current) return
    const mm = Markmap.create(svgRef.current, { autoFit: true }, data)
    return () => mm.destroy()
  }, [data])

  return <svg ref={svgRef} className="h-[520px] w-full rounded-lg border bg-white" />
}

