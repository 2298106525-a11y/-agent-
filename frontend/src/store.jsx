import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { getStudentFull, toggleProgress, saveTestScore as apiSaveTestScore, saveStudentResult, saveStudentStep } from './api/client'
import api from './api/client'

const StoreContext = createContext(null)

const DEFAULT_ITEMS = { learning: {}, training: {}, testScore: null, testCorrect: null, testTotal: null }

export function StoreProvider({ children }) {
  const [studentName, setStudentName] = useState('')
  const [result, setResult] = useState(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [completedItems, setCompletedItems] = useState(DEFAULT_ITEMS)
  const currentStepRef = useRef(0)
  useEffect(() => { currentStepRef.current = currentStep }, [currentStep])

  /** 确保学生在数据库中存在（只创建记录，不覆盖已有数据） */
  const ensureStudent = useCallback(async (name) => {
    if (!name) return
    try {
      const res = await getStudentFull(name)
      if (!res?.data?.student) {
        // 学生不存在，创建空记录
        await saveStudentStep(name, 0)
      }
      // 学生已存在，不做任何写入，避免覆盖
    } catch (e) { console.error('[store] ensureStudent error:', e) }
  }, [])

  /** 切换学生：从数据库加载数据 */
  const switchStudent = useCallback(async (name) => {
    setStudentName(name)
    // 确保学生在数据库中存在
    await ensureStudent(name)
    try {
      const res = await getStudentFull(name)
      if (res?.data) {
        const d = res.data
        setResult(d.result || null)
        setCurrentStep(d.currentStep || 0)
        setCompletedItems(d.completedItems || DEFAULT_ITEMS)
      } else {
        setResult(null)
        setCurrentStep(0)
        setCompletedItems(DEFAULT_ITEMS)
      }
    } catch {
      setResult(null)
      setCurrentStep(0)
      setCompletedItems(DEFAULT_ITEMS)
    }
  }, [ensureStudent])

  /** 保存 result 到数据库 */
  const saveResult = useCallback(async (name, data, step = 0) => {
    if (!name || !data) return
    try {
      await saveStudentResult(name, data, data?.framework?.position_name || '', '初级', step)
    } catch (e) { console.error('[store] saveResult error:', e) }
  }, [])

  /** 保存 currentStep 到数据库 */
  const saveStep = useCallback(async (name, step) => {
    if (!name) return
    try {
      await saveStudentStep(name, step)
    } catch (e) { console.error('[store] saveStep error:', e) }
  }, [])

  // result 变化时保存到数据库
  useEffect(() => {
    if (!studentName || !result) return
    saveResult(studentName, result, currentStepRef.current)
  }, [studentName, result]) // eslint-disable-line

  // currentStep 变化时保存到数据库
  useEffect(() => {
    if (!studentName) return
    saveStep(studentName, currentStep)
  }, [studentName, currentStep]) // eslint-disable-line

  /** 切换学习模块完成状态 */
  const completeLearning = useCallback(async (moduleId) => {
    setCompletedItems(prev => {
      const learning = { ...prev.learning }
      if (learning[moduleId]) delete learning[moduleId]
      else learning[moduleId] = true
      return { ...prev, learning }
    })
    if (studentName) {
      try { await toggleProgress(studentName, 'learning', moduleId) } catch (e) { console.error('[store] toggle learning error:', e) }
    }
  }, [studentName])

  /** 切换训练任务完成状态 */
  const completeTraining = useCallback(async (taskId) => {
    setCompletedItems(prev => {
      const training = { ...prev.training }
      if (training[taskId]) delete training[taskId]
      else training[taskId] = true
      return { ...prev, training }
    })
    if (studentName) {
      try { await toggleProgress(studentName, 'training', taskId) } catch (e) { console.error('[store] toggle training error:', e) }
    }
  }, [studentName])

  /** 保存考核成绩 */
  const saveTestScore = useCallback(async (score, correct, total) => {
    setCompletedItems(prev => ({ ...prev, testScore: score, testCorrect: correct, testTotal: total }))
    if (studentName) {
      try { await apiSaveTestScore(studentName, score, correct, total) } catch (e) { console.error('[store] saveTestScore error:', e) }
    }
  }, [studentName])

  /** 重置 */
  const reset = useCallback(() => {
    setStudentName('')
    setResult(null)
    setCurrentStep(0)
    setCompletedItems(DEFAULT_ITEMS)
  }, [])

  return (
    <StoreContext.Provider value={{
      result, setResult, currentStep, setCurrentStep,
      studentName, setStudentName, completedItems, setCompletedItems,
      switchStudent, saveResult,
      completeLearning, completeTraining, saveTestScore, reset,
    }}>
      {children}
    </StoreContext.Provider>
  )
}

export function useStore() {
  const ctx = useContext(StoreContext)
  if (!ctx) throw new Error('useStore must be used within StoreProvider')
  return ctx
}
