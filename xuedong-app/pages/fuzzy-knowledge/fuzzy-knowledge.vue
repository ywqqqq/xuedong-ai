<template>
	<view class="container">
		<view class="knowledge-list">
			<view v-for="(item, index) in knowledgeList" 
				:key="index" 
				class="knowledge-item"
				:style="getFrequencyStyle(item.frequency)">
				<view class="knowledge-content">
					<text class="knowledge-text">{{ item.content }}</text>
					<text class="frequency-badge">{{ item.frequency }}</text>
				</view>
				<view class="knowledge-time">{{ formatTime(item.time) }}</view>
			</view>
		</view>
	</view>
</template>

<script>
export default {
	data() {
		return {
			knowledgeList: [
				{
					title: '三角函数',
						content: '三角函数是研究角度与边长比值关系的重要函数。包括：\n• 正弦函数(sin)\n• 余弦函数(cos)\n• 正切函数(tan)\n主要应用于测量、物理运动、工程计算等领域。',
						time: new Date('2024-01-10').getTime(),
						frequency: 5
				},
				{
					title: '函数基础',
						content: '函数是描述两个变量之间对应关系的数学概念。重点包括：\n• 函数的定义域和值域\n• 函数的性质（单调性、奇偶性）\n• 基本初等函数的图像特征\n• 复合函数与反函数',
						time: new Date('2024-01-09').getTime(),
						frequency: 4
				},
				{
					title: '导数',
						content: '导数表示函数在某一点的变化率。核心内容：\n• 导数的定义和几何意义\n• 基本求导法则\n• 复合函数求导\n• 导数在实际问题中的应用',
						time: new Date('2024-01-08').getTime(),
						frequency: 2
				},
				{
					title: '积分',
						content: '积分是微积分中的重要概念，用于计算曲线下的面积。包括：\n• 定积分和不定积分的概念\n• 基本积分公式\n• 换元积分法和分部积分法\n• 积分在面积和体积计算中的应用',
						time: new Date('2024-01-07').getTime(),
						frequency: 2
				},
				{
					title: '概率',
						content: '概率用于描述随机事件发生的可能性。主要内容：\n• 随机事件与概率的定义\n• 古典概型与几何概型\n• 条件概率与全概率公式\n• 概率在统计分析中的应用',
						time: new Date('2024-01-06').getTime(),
						frequency: 1
				}
			]
		}
	},
	methods: {
		formatTime(timestamp) {
			// 检查 timestamp 是否有效
			if (!timestamp) {
				return '未知时间';
			}
			
			// 如果 timestamp 是字符串，需要转换
			const date = new Date(typeof timestamp === 'string' ? timestamp : Number(timestamp));
			
			// 检查日期是否有效
			if (isNaN(date.getTime())) {
				return '未知时间';
			}
			
			const now = new Date();
			
			// 今天的日期（去除时分秒）
			const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
			// 传入日期（去除时分秒）
			const targetDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
			
			// 计算天数差
			const daysDiff = Math.floor((today - targetDate) / (1000 * 60 * 60 * 24));
			
			if (daysDiff === 0) {
				return '今天';
			} else if (daysDiff === 1) {
				return '昨天';
			} else {
				// 确保月份和日期是有效的
				const month = date.getMonth() + 1;
				const day = date.getDate();
				return `${month}月${day}日`;
			}
		},
		getFrequencyStyle(frequency) {
			// 根据频率返回不同的样式
			if (frequency > 5) {
				return 'background-color: #ff4d4f; color: white;';
			} else if (frequency > 3) {
				return 'background-color: #ffa940; color: white;';
			} else if (frequency > 0) {
				return 'background-color: #bae637; color: black;';
			}
			return 'background-color: #d9d9d9; color: black;';
		}
	},
	onLoad() {
		// 不需要调用接口，直接使用静态数据
	}
}
</script>

<style>
.container {
	background-color: #1c1c1e;
	min-height: 100vh;
}

.knowledge-list {
	padding: 16px;
}

.knowledge-item {
	padding: 12px 16px;
	margin-bottom: 12px;
	border-radius: 8px;
	transition: all 0.3s ease;
}

.knowledge-item:active {
	opacity: 0.7;
}

.knowledge-content {
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.knowledge-text {
	flex: 1;
	font-size: 16px;
	line-height: 1.5;
}

.frequency-badge {
	min-width: 24px;
	height: 24px;
	padding: 0 8px;
	border-radius: 12px;
	background-color: rgba(0, 0, 0, 0.1);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
	margin-left: 12px;
}

.knowledge-time {
	font-size: 12px;
	margin-top: 8px;
	opacity: 0.7;
}

.empty-state {
	display: flex;
	justify-content: center;
	align-items: center;
	height: 200px;
}

.empty-text {
	color: #808080;
	font-size: 16px;
}

.knowledge-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 12px;
}

.knowledge-frequency {
	display: flex;
	align-items: center;
	background-color: rgba(0, 122, 255, 0.1);
	padding: 4px 8px;
	border-radius: 12px;
}

.frequency-count {
	color: #007AFF;
	font-size: 16px;
	font-weight: bold;
	margin-right: 4px;
}

.frequency-label {
	color: #007AFF;
	font-size: 12px;
}

.knowledge-title {
	flex: 1;
	margin-bottom: 0;
	margin-right: 12px;
}
</style> 