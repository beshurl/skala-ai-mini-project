/** Run through cua_repl, using the documented tab.playwright API for every UI action.
 * const {run}=await import('/absolute/project/frontend/scripts/browser_e2e.mjs'); await run(tab)
 * No external browser transport, private page state, or fabricated progress is used.
 */
import assert from 'node:assert/strict'

export async function run(tab, {backend='mlx'} = {}) {
  const p=tab.playwright, steps=[]
  if (await p.getByRole('button',{name:'합성 사건 열기',exact:true}).isVisible()) {
    await p.getByRole('button',{name:'합성 사건 열기',exact:true}).click()
  }
  await p.getByRole('button',{name:'새 합성 사건 추가',exact:true}).waitFor({state:'visible'})
  await p.getByRole('button',{name:'새 합성 사건 추가',exact:true}).click()
  await p.getByText('실행 모델 정보',{exact:true}).click()
  await p.getByText(backend,{exact:true}).waitFor({state:'visible'})
  if(backend==='mlx') assert.ok(await p.getByText('확인됨',{exact:true}).isVisible(),'A real, loaded adapter is required for this run')
  await p.getByText('실행 모델 정보',{exact:true}).click()
  // Account history retains earlier fixture copies; the newest set is listed first.
  await p.getByRole('button',{name:/사라진 연구 노트 합성 기록/}).first().click()
  await p.getByRole('heading',{name:'사라진 연구 노트',exact:true}).waitFor({state:'visible'})
  assert.equal(await p.getByRole('heading',{name:'본인 확인이 완료된 기록',exact:true}).count(),0)
  await tab.getAXState({emit:false})
  steps.push('Explicit demo entry; select case; unreleased evidence not in DOM')
  await p.getByRole('button',{name:'분석 시작',exact:true}).click()
  await p.getByRole('status').filter({hasText:'분석 완료'}).waitFor({state:'visible'})
  assert.equal(await p.locator('.label').innerText(),'추가 확인 필요')
  await p.locator('.event-panel summary').click()
  await p.getByText('결과 저장 완료',{exact:true}).waitFor({state:'visible'})
  await p.locator('.event-panel summary').click()
  await tab.getAXState({emit:false})
  steps.push('v1 real progress events and INSUFFICIENT result')
  await p.getByRole('button',{name:/새 증거 공개.*2건 대기/}).click()
  await p.getByRole('heading',{name:'본인 확인이 완료된 기록',exact:true}).waitFor({state:'visible'})
  await p.getByRole('button',{name:'현재 증거로 재분석',exact:true}).click()
  await p.getByRole('status').filter({hasText:'분석 완료'}).waitFor({state:'visible'})
  assert.equal(await p.locator('.label').innerText(),'자료 간 충돌')
  await p.getByRole('button',{name:'본인 확인이 완료된 기록 ↗',exact:true}).click()
  const citationTarget=await p.locator('.evidence-record.highlighted').innerText()
  assert.match(citationTarget,/본인 확인이 완료된 출입 기록/)
  const select=p.getByLabel('비교할 이전 분석')
  await select.selectOption({index:1})
  await p.getByRole('button',{name:'결과 비교',exact:true}).click()
  await p.getByTestId('comparison').getByText('판단 변경',{exact:true}).waitFor({state:'visible'})
  await tab.getAXState({emit:false})
  steps.push('v2 CONTRADICTED, citation opens actual source, version comparison changes')
  await p.getByRole('button',{name:/새 증거 공개.*1건 대기/}).click()
  await p.getByRole('heading',{name:'주변 날씨 기록',exact:true}).waitFor({state:'visible'})
  await p.getByRole('button',{name:'현재 증거로 재분석',exact:true}).click()
  await p.getByRole('status').filter({hasText:'분석 완료'}).waitFor({state:'visible'})
  assert.equal(await p.locator('.label').innerText(),'자료 간 충돌')
  await select.selectOption({index:1})
  await p.getByRole('button',{name:'결과 비교',exact:true}).click()
  await p.getByTestId('comparison').getByText('판단 유지',{exact:true}).waitFor({state:'visible'})
  await tab.getAXState({emit:false})
  steps.push('v3 irrelevant evidence keeps prior conclusion')
  const layout=await p.locator('html').evaluate(el=>({width:el.clientWidth,scrollWidth:el.scrollWidth}))
  assert.ok(layout.scrollWidth<=layout.width+1,`Horizontal overflow: ${JSON.stringify(layout)}`)
  steps.push('No horizontal overflow at observed browser viewport')
  return {status:'PASS',browser:'cua_repl IAB',backend:backend==='mlx'?'mlx; adapter confirmed through UI':'explicit fixture; no MLX inference',started_from:'fresh synthetic demo',steps,viewport:layout,completed_at:new Date().toISOString()}
}
