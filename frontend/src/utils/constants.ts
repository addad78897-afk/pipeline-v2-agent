export interface StepDefinition {
  number: number
  name: string
  description: string
  phase: 1 | 2 | 3
  script: string
  color: 'cyan' | 'magenta' | 'amber'
}

export const PHASES = [
  { id: 1, name: '规则引擎（文书解析）', color: 'cyan' as const, steps: [1, 2, 3, 4, 5, 6] },
  { id: 2, name: 'LLM 提取（DeepSeek）', color: 'magenta' as const, steps: [7, 8, 9, 10] },
  { id: 3, name: '高级分析与统计', color: 'amber' as const, steps: [11, 12, 13, 14, 15, 16] },
]

export const STEPS: StepDefinition[] = [
  { number: 1, name: '编码检测与转换', description: '检测文件编码（UTF-8/GBK/GB18030）并统一转为UTF-8', phase: 1, script: '0001_编码检测与转换.py', color: 'cyan' },
  { number: 2, name: '段落分割', description: '按判决书结构切分：原告诉称、被告辩称、本院查明、本院认为、判决如下等', phase: 1, script: '0002_段落分割.py', color: 'cyan' },
  { number: 3, name: '案号与法院提取', description: '提取案号、法院全称、省份、法院层级、文书类型', phase: 1, script: '0003_案号与法院提取.py', color: 'cyan' },
  { number: 4, name: '当事人信息提取', description: '提取原告、被告、上诉人、被上诉人、第三人、代理人', phase: 1, script: '0004_当事人信息提取.py', color: 'cyan' },
  { number: 5, name: '主体分类', description: '将当事人分类为自然人、企业、个体工商户', phase: 1, script: '0005_主体分类_自然人企业个体工商户.py', color: 'cyan' },
  { number: 6, name: '名称规范化', description: '统一公司全称→简称、自然人姓名去重、法院名称标准化', phase: 1, script: '0006_名称规范化.py', color: 'cyan' },
  { number: 7, name: 'Round 1 字段提取', description: 'DeepSeek-chat批量提取：原告诉请、判赔金额、法定赔偿率等核心字段', phase: 2, script: '0007_第一轮_批量字段提取.py', color: 'magenta' },
  { number: 8, name: 'Round 2 深度提取', description: '对835条高值案件深度数值提取与交叉验算', phase: 2, script: '0008_第二轮_深度数值提取与验算.py', color: 'magenta' },
  { number: 9, name: '手工分类补丁', description: '对AI分类边界模糊的案例进行人工修正', phase: 2, script: '0009_手工分类数据补丁.py', color: 'magenta' },
  { number: 10, name: '19维综合分析', description: 'DeepSeek多维度AI综合分析：侵权认定、赔偿方式、行业分类等19个维度', phase: 2, script: '0010_多维度AI综合分析_19维.py', color: 'magenta' },
  { number: 11, name: '可视化（6图）', description: '生成年度趋势、法院层级、行业判赔差异等6张统计图表', phase: 3, script: '0011_可视化_6图.py', color: 'amber' },
  { number: 12, name: '证据类型与说理', description: '分析证据类型分布和判决书说理深度', phase: 3, script: '0012_证据类型与说理深度.py', color: 'amber' },
  { number: 13, name: '同案不同判分析', description: '检测相似案情下的裁判冲突', phase: 3, script: '0013_同案不同判冲突分析.py', color: 'amber' },
  { number: 14, name: '阶梯式证明标准', description: '构建证据标准的三阶梯分类模型', phase: 3, script: '0014_阶梯式证明标准模型.py', color: 'amber' },
  { number: 15, name: '计量经济学建模', description: '多元回归、Logistic模型等4个计量经济模型', phase: 3, script: '0015_计量经济学建模_4模型.py', color: 'amber' },
  { number: 16, name: '时间趋势分析', description: '年度-月度案件量、判赔额、法定赔偿率的时间序列分析', phase: 3, script: '0016_时间趋势分析.py', color: 'amber' },
]

export type StepStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface StepState {
  number: number
  status: StepStatus
  startedAt?: string
  completedAt?: string
  log: string[]
  error?: string
}

export type JobStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export interface Job {
  jobId: string
  sessionId: string
  status: JobStatus
  progressPercent: number
  currentStep: number
  steps: StepState[]
  fileCount: number
  createdAt: string
}
